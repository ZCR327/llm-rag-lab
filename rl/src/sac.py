# -*- coding: utf-8 -*-
"""
sac.py — SAC (Soft Actor-Critic) from scratch (PyTorch + gymnasium)

D4ML 课程项目 v0.4 - 第 3 个 RL 算法:
- 最大熵框架 (Haarnoja 2018): 最大化 E[Σ r_t + α·H(π(·|s_t))]
- Twin Q (双 Q 网络, 取 min 防 Q 过估计)
- 自动 α 调优 (target_entropy = -|A|)
- Stochastic policy (Categorical 离散, CartPole 适用)
- Off-policy + Replay buffer (与 DQN 类似)

用法:
  python src/sac.py --episodes 600
  python src/sac.py --quick  # 100 ep
"""
import os
import sys
import argparse
import time
import random
from collections import deque
from pathlib import Path
from typing import Tuple, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical
import gymnasium as gym


# ======================== Hyperparameters ========================

SEED = 42
GAMMA = 0.99
TAU = 0.005               # soft target update rate
LR_ACTOR = 3e-4
LR_CRITIC = 3e-4
LR_ALPHA = 3e-4
HIDDEN = 64
BUFFER_SIZE = 50_000
BATCH_SIZE = 128
MAX_EPISODES = 1000
LOG_EVERY = 10
START_STEPS = 1000         # 初始随机步数, 填满 buffer 再开始训练
UPDATE_EVERY = 1           # 每 1 步训练 1 次 (SAC 1:1 sample-efficient)


# ======================== Networks ========================

class Actor(nn.Module):
    """Stochastic policy: state -> hidden -> logits (Categorical 离散动作)"""

    def __init__(self, state_dim: int, num_actions: int, hidden: int = HIDDEN):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, num_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

    def sample(self, state: torch.Tensor):
        """采样动作, 返回 (action, log_prob, probs)"""
        logits = self.forward(state)
        dist = Categorical(logits=logits)
        action = dist.sample()
        lp = dist.log_prob(action)
        probs = dist.probs
        return action, lp, probs

    def get_log_prob_and_entropy(self, state: torch.Tensor, action: torch.Tensor):
        """给 Q 训练用: 给定 state+action, 返回 log_prob 和 entropy"""
        logits = self.forward(state)
        dist = Categorical(logits=logits)
        lp = dist.log_prob(action)
        entropy = dist.entropy()
        return lp, entropy


class QNet(nn.Module):
    """Q(s, a) 标量网络"""

    def __init__(self, state_dim: int, num_actions: int, hidden: int = HIDDEN):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, num_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ======================== Replay Buffer ========================

class ReplayBuffer:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buf = deque(maxlen=capacity)

    def push(self, s, a, r, s_next, done):
        self.buf.append((s, a, r, s_next, done))

    def sample(self, batch_size: int):
        batch = random.sample(self.buf, batch_size)
        s, a, r, s_next, done = zip(*batch)
        return (
            torch.tensor(np.array(s), dtype=torch.float32),
            torch.tensor(a, dtype=torch.long),
            torch.tensor(r, dtype=torch.float32),
            torch.tensor(np.array(s_next), dtype=torch.float32),
            torch.tensor(done, dtype=torch.float32),
        )

    def __len__(self):
        return len(self.buf)


# ======================== SAC Agent ========================

class SACAgent:
    def __init__(self, state_dim: int, num_actions: int):
        torch.manual_seed(SEED)
        np.random.seed(SEED)
        random.seed(SEED)

        self.num_actions = num_actions

        # Networks
        self.actor = Actor(state_dim, num_actions)
        self.q1 = QNet(state_dim, num_actions)
        self.q2 = QNet(state_dim, num_actions)
        # Target Q (Polyak averaging)
        self.q1_target = QNet(state_dim, num_actions)
        self.q2_target = QNet(state_dim, num_actions)
        self.q1_target.load_state_dict(self.q1.state_dict())
        self.q2_target.load_state_dict(self.q2.state_dict())
        for p in self.q1_target.parameters(): p.requires_grad = False
        for p in self.q2_target.parameters(): p.requires_grad = False

        # Optimizers
        self.opt_actor = optim.Adam(self.actor.parameters(), lr=LR_ACTOR)
        self.opt_q1 = optim.Adam(self.q1.parameters(), lr=LR_CRITIC)
        self.opt_q2 = optim.Adam(self.q2.parameters(), lr=LR_CRITIC)

        # 自动 α 调优 (target_entropy = -log(|A|) ≈ -0.69)
        # v0.1 用 -|A|=-2 让 α 衰减过快, 探索不足 → 策略 collapse
        # v0.2 改 -log(|A|) 让熵目标更宽松, 保持探索
        import numpy as _np
        self.target_entropy = -_np.log(num_actions)
        self.log_alpha = torch.zeros(1, requires_grad=True)
        self.opt_alpha = optim.Adam([self.log_alpha], lr=LR_ALPHA)

        self.buffer = ReplayBuffer(BUFFER_SIZE)

    @property
    def alpha(self) -> torch.Tensor:
        return self.log_alpha.exp()

    def select_action(self, state: np.ndarray, deterministic: bool = False) -> int:
        with torch.no_grad():
            s = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            logits = self.actor(s)
            if deterministic:
                a = int(logits.argmax(dim=1).item())
            else:
                dist = Categorical(logits=logits)
                a = int(dist.sample().item())
        return a

    def soft_update(self, target, source: nn.Module):
        """Polyak averaging: target = τ·source + (1-τ)·target"""
        for tp, sp in zip(target.parameters(), source.parameters()):
            tp.data.mul_(1.0 - TAU).add_(TAU * sp.data)

    def train_step(self) -> dict | None:
        if len(self.buffer) < BATCH_SIZE:
            return None
        s, a, r, s_next, done = self.buffer.sample(BATCH_SIZE)

        # ====== 1. 更新 Q1, Q2 ======
        with torch.no_grad():
            # 离散 SAC 关键 fix: V(s') = Σ_a π(a'|s') · min(Q1(s',a'), Q2(s',a'))
            # 不再用 sampled a_next (高方差), 而是 full enumeration
            logits_next = self.actor(s_next)
            probs_next = F.softmax(logits_next, dim=-1)  # (B, num_actions)
            q1_t = self.q1_target(s_next)  # (B, num_actions)
            q2_t = self.q2_target(s_next)
            q_min = torch.min(q1_t, q2_t)  # (B, num_actions)
            v_next = (probs_next * q_min).sum(dim=-1)  # (B,) scalar V(s')
            target_q = r + GAMMA * (1.0 - done) * v_next

        q1_pred = self.q1(s).gather(1, a.unsqueeze(1)).squeeze(1)
        q2_pred = self.q2(s).gather(1, a.unsqueeze(1)).squeeze(1)
        q1_loss = F.mse_loss(q1_pred, target_q)
        q2_loss = F.mse_loss(q2_pred, target_q)
        self.opt_q1.zero_grad(); q1_loss.backward(); self.opt_q1.step()
        self.opt_q2.zero_grad(); q2_loss.backward(); self.opt_q2.step()

        # ====== 2. 更新 Actor + α ======
        # Freeze Q for actor update
        for p in self.q1.parameters(): p.requires_grad = False
        for p in self.q2.parameters(): p.requires_grad = False

        lp, entropy = self.actor.get_log_prob_and_entropy(s, a)
        q1_a = self.q1(s).gather(1, a.unsqueeze(1)).squeeze(1)
        q2_a = self.q2(s).gather(1, a.unsqueeze(1)).squeeze(1)
        q_min = torch.min(q1_a, q2_a)
        # J_π = E[α·log π - Q]  (与 V(s') 的 fix 配套, 这里只用当前 batch)
        actor_loss = (self.alpha.detach() * lp - q_min).mean()
        self.opt_actor.zero_grad(); actor_loss.backward(); self.opt_actor.step()

        # 自动 α: 让 entropy 趋近 target_entropy
        alpha_loss = -(self.log_alpha * (lp.detach() + self.target_entropy)).mean()
        self.opt_alpha.zero_grad(); alpha_loss.backward(); self.opt_alpha.step()

        # Unfreeze Q
        for p in self.q1.parameters(): p.requires_grad = True
        for p in self.q2.parameters(): p.requires_grad = True

        # ====== 3. 软更新 target ======
        self.soft_update(self.q1_target, self.q1)
        self.soft_update(self.q2_target, self.q2)

        return {
            "q1_loss": float(q1_loss.item()),
            "q2_loss": float(q2_loss.item()),
            "actor_loss": float(actor_loss.item()),
            "alpha_loss": float(alpha_loss.item()),
            "alpha": float(self.alpha.item()),
            "entropy": float(entropy.mean().item()),
        }


# ======================== Training ========================

def train(env_name: str = "CartPole-v1", save_path: Path = None,
          max_episodes: int = MAX_EPISODES) -> SACAgent:
    env = gym.make(env_name)
    state_dim = env.observation_space.shape[0]
    num_actions = env.action_space.n
    print(f"[env] {env_name} state_dim={state_dim} num_actions={num_actions}")

    agent = SACAgent(state_dim, num_actions)
    recent_returns = deque(maxlen=100)
    best_avg = -float("inf")
    start = time.time()
    step_count = 0
    ep = 0

    while ep < max_episodes:
        s, _ = env.reset(seed=SEED + ep)
        ep_return = 0.0
        ep_steps = 0

        for t in range(env.spec.max_episode_steps):
            # 初始随机步数填 buffer
            if step_count < START_STEPS:
                a = env.action_space.sample()
            else:
                a = agent.select_action(s)
            s_next, r, terminated, truncated, _ = env.step(a)
            done = terminated or truncated
            agent.buffer.push(s, a, r, s_next, float(done))
            s = s_next
            ep_return += r
            step_count += 1
            ep_steps += 1

            # 训练
            if step_count >= START_STEPS:
                losses = agent.train_step()

            if done:
                break

        ep += 1
        recent_returns.append(ep_return)

        if ep % LOG_EVERY == 0:
            avg = np.mean(recent_returns)
            elapsed = time.time() - start
            print(
                f"[ep {ep:4d}] return={ep_return:6.1f} avg100={avg:6.1f} "
                f"alpha={agent.alpha.item():.3f} step={step_count} t={elapsed:.1f}s"
            )
            if avg > best_avg:
                best_avg = avg
                if save_path:
                    torch.save({
                        "actor": agent.actor.state_dict(),
                        "q1": agent.q1.state_dict(),
                        "q2": agent.q2.state_dict(),
                        "log_alpha": agent.log_alpha,
                    }, save_path)
                    print(f"  ★ saved best (avg={avg:.1f}) → {save_path}")

        if len(recent_returns) >= 100 and np.mean(recent_returns) >= 475:
            print(f"\n[✓] SOLVED at episode {ep} (avg100={np.mean(recent_returns):.1f})")
            if save_path:
                torch.save({
                    "actor": agent.actor.state_dict(),
                    "q1": agent.q1.state_dict(),
                    "q2": agent.q2.state_dict(),
                    "log_alpha": agent.log_alpha,
                }, save_path)
            break

    env.close()
    return agent


def evaluate(agent: SACAgent, env_name: str = "CartPole-v1", episodes: int = 20) -> float:
    env = gym.make(env_name)
    returns = []
    for ep in range(episodes):
        s, _ = env.reset(seed=1000 + ep)
        ep_return = 0.0
        for t in range(env.spec.max_episode_steps):
            a = agent.select_action(s, deterministic=True)
            s, r, terminated, truncated, _ = env.step(a)
            ep_return += r
            if terminated or truncated:
                break
        returns.append(ep_return)
    env.close()
    avg = np.mean(returns)
    print(f"\n[eval] {env_name} over {episodes} eps: avg={avg:.1f}, min={min(returns):.0f}, max={max(returns):.0f}")
    return avg


# ======================== CLI ========================

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=MAX_EPISODES)
    p.add_argument("--quick", action="store_true")
    p.add_argument("--env", default="CartPole-v1")
    args = p.parse_args()

    if args.quick:
        args.episodes = 200
        START_STEPS = 500  # 快速测试少填 buffer

    save = Path(__file__).resolve().parent.parent / "checkpoints" / "sac_v2_cartpole.pt"
    save.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"D4ML — SAC v0.2 (discrete V(s') fix) from scratch on {args.env}")
    print(f"  γ={GAMMA} τ={TAU} lr_actor={LR_ACTOR} lr_critic={LR_CRITIC}")
    print(f"  buffer={BUFFER_SIZE} batch={BATCH_SIZE} start_steps={START_STEPS}")
    print("  v0.2 fix: V(s') = sum_a pi(a'|s') * min(Q1,Q2)  (full enumeration, no sampling bias)")
    print("=" * 60)

    agent = train(args.env, save_path=save, max_episodes=args.episodes)
    print("\n--- final evaluation ---")
    evaluate(agent, args.env, episodes=20)