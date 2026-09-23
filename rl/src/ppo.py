# -*- coding: utf-8 -*-
"""
ppo.py — PPO (Proximal Policy Optimization) from scratch (PyTorch + gymnasium)

D4ML 课程项目 v0.3:
- on-policy policy gradient + clipped surrogate objective (Schulman 2017)
- Actor-Critic 网络: 共享 backbone + actor head (logits) + critic head (V)
- GAE (Generalized Advantage Estimation) 计算 advantage
- CartPole-v1 测试 (离散动作 2 个, 状态 4 维)

用法:
  python src/ppo.py
  python src/ppo.py --episodes 500
  python src/ppo.py --quick  # 200 ep 测试
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
GAMMA = 0.99                # discount factor
GAE_LAMBDA = 0.95           # GAE 衰减
CLIP_EPS = 0.2              # PPO clipped objective 范围
ENTROPY_COEF = 0.01         # 熵正则 (鼓励探索)
VALUE_COEF = 0.5            # critic loss 权重
MAX_GRAD_NORM = 0.5         # 梯度裁剪
HIDDEN = 64

# Rollout 收集参数
ROLLOUT_LEN = 500           # 每个 rollout 步数 (CartPole max_episode_steps=500)

# 更新参数
EPOCHS = 4                  # 每 rollout 训练的 epoch 数
MINIBATCH_SIZE = 64         # minibatch 大小 (CartPole buffer 500 / 64 ≈ 8 minibatch)

# 优化器
LR_ACTOR = 3e-4
LR_CRITIC = 1e-3

MAX_EPISODES = 1000         # 训练上限
LOG_EVERY = 10


# ======================== Actor-Critic 网络 ========================

class ActorCritic(nn.Module):
    """共享 backbone + actor head (logits) + critic head (V(s))"""

    def __init__(self, state_dim: int, num_actions: int, hidden: int = HIDDEN):
        super().__init__()
        # 共享特征层
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
        )
        # Actor: 输出每个动作的 logits (离散)
        self.actor = nn.Linear(hidden, num_actions)
        # Critic: 输出 V(s) 标量
        self.critic = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        feat = self.shared(x)
        return self.actor(feat), self.critic(feat)

    def get_action(self, state: np.ndarray, deterministic: bool = False):
        """采样动作, 返回 (action, log_prob, value)"""
        with torch.no_grad():
            s = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            logits, value = self.forward(s)
            if deterministic:
                action = int(logits.argmax(dim=1).item())
                log_prob = torch.zeros(1)  # 不用
            else:
                dist = Categorical(logits=logits)
                action_t = dist.sample()
                action = int(action_t.item())
                log_prob = dist.log_prob(action_t)
        return action, float(log_prob.item()), float(value.item())

    def evaluate(self, states: torch.Tensor, actions: torch.Tensor):
        """批量计算 log_prob + entropy + value"""
        logits, values = self.forward(states)
        dist = Categorical(logits=logits)
        log_probs = dist.log_prob(actions)
        entropy = dist.entropy()
        return log_probs, entropy, values.squeeze(-1)


# ======================== GAE 计算 ========================

def compute_gae(rewards: List[float], values: List[float], dones: List[bool],
                last_value: float = 0.0,
                gamma: float = GAMMA, lam: float = GAE_LAMBDA) -> Tuple[np.ndarray, np.ndarray]:
    """Generalized Advantage Estimation
    A_t = sum_l (γλ)^l δ_{t+l},  δ_t = r_t + γV(s_{t+1})(1-done_t) - V(s_t)
    last_value 用于 bootstrap (末状态不是 terminal 时, 用 V(s_{T+1}) 估计)
    """
    rewards = np.array(rewards, dtype=np.float32)
    values = np.array(values, dtype=np.float32)
    dones = np.array(dones, dtype=np.float32)
    T = len(rewards)
    advantages = np.zeros(T, dtype=np.float32)
    last_adv = 0.0
    last_val = last_value * (1.0 - dones[-1])  # bootstrap (若末状态 done, V=0)
    for t in reversed(range(T)):
        delta = rewards[t] + gamma * last_val * (1.0 - dones[t]) - values[t]
        advantages[t] = last_adv = delta + gamma * lam * (1.0 - dones[t]) * last_adv
        last_val = values[t]
    returns = advantages + values
    return advantages, returns


# ======================== Rollout Buffer ========================

class RolloutBuffer:
    """on-policy rollout, 训练完就丢"""

    def __init__(self):
        self.states: List[np.ndarray] = []
        self.actions: List[int] = []
        self.log_probs: List[float] = []
        self.rewards: List[float] = []
        self.values: List[float] = []
        self.dones: List[bool] = []

    def push(self, s, a, lp, r, v, d):
        self.states.append(s)
        self.actions.append(a)
        self.log_probs.append(lp)
        self.rewards.append(r)
        self.values.append(v)
        self.dones.append(d)

    def __len__(self):
        return len(self.states)

    def get(self):
        return (
            np.array(self.states, dtype=np.float32),
            np.array(self.actions, dtype=np.int64),
            np.array(self.log_probs, dtype=np.float32),
            np.array(self.rewards, dtype=np.float32),
            np.array(self.values, dtype=np.float32),
            np.array(self.dones, dtype=np.float32),
        )

    def clear(self):
        self.states.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.values.clear()
        self.dones.clear()


# ======================== PPO Trainer ========================

def compute_gae_simple(rewards, values, dones, gamma, lam):
    """独立 GAE 函数"""
    return compute_gae(rewards, values, dones, gamma, lam)


def ppo_update(actor_critic: ActorCritic, optimizer_actor, optimizer_critic,
              buffer: RolloutBuffer) -> dict:
    """一次 PPO 更新 (用 buffer 全部数据, 切 minibatch 跑 EPOCHS 遍)"""
    states, actions, old_log_probs, rewards, values, dones = buffer.get()
    # last_value 已在 train() 里 bootstrap 进 buffer.values 末尾
    # 取出 (跟 states 一样长)
    last_v = values[-1]
    values_for_gae = values[:-1]  # 去掉 bootstrap, 跟 rewards/dones 对齐
    advantages, returns = compute_gae(
        rewards.tolist(), values_for_gae.tolist(), dones.tolist(),
        last_value=last_v, gamma=GAMMA, lam=GAE_LAMBDA,
    )

    # 优势归一化 (关键: 减少方差)
    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

    # Tensor 化
    states_t = torch.tensor(states, dtype=torch.float32)
    actions_t = torch.tensor(actions, dtype=torch.long)
    old_log_probs_t = torch.tensor(old_log_probs, dtype=torch.float32)
    advantages_t = torch.tensor(advantages, dtype=torch.float32)
    returns_t = torch.tensor(returns, dtype=torch.float32)

    n = len(states)
    idx = np.arange(n)
    total_policy_loss = 0.0
    total_value_loss = 0.0
    total_entropy = 0.0
    n_batches = 0

    for _ in range(EPOCHS):
        np.random.shuffle(idx)
        for start in range(0, n, MINIBATCH_SIZE):
            end = start + MINIBATCH_SIZE
            mb = idx[start:end]
            mb_t = torch.tensor(mb, dtype=torch.long)

            mb_states = states_t[mb_t]
            mb_actions = actions_t[mb_t]
            mb_old_lp = old_log_probs_t[mb_t]
            mb_adv = advantages_t[mb_t]
            mb_ret = returns_t[mb_t]

            # 当前策略的 log_prob + entropy
            new_lp, entropy, values_pred = actor_critic.evaluate(mb_states, mb_actions)
            ratio = torch.exp(new_lp - mb_old_lp)

            # PPO clipped surrogate objective
            surr1 = ratio * mb_adv
            surr2 = torch.clamp(ratio, 1.0 - CLIP_EPS, 1.0 + CLIP_EPS) * mb_adv
            policy_loss = -torch.min(surr1, surr2).mean()

            # Value loss (MSE)
            value_loss = F.mse_loss(values_pred, mb_ret)

            # 总 loss (entropy bonus)
            entropy_loss = entropy.mean()
            loss = policy_loss + VALUE_COEF * value_loss - ENTROPY_COEF * entropy_loss

            # 优化 (分开 optimizer)
            optimizer_actor.zero_grad()
            optimizer_critic.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(actor_critic.parameters(), MAX_GRAD_NORM)
            optimizer_actor.step()
            optimizer_critic.step()

            total_policy_loss += float(policy_loss.item())
            total_value_loss += float(value_loss.item())
            total_entropy += float(entropy_loss.item())
            n_batches += 1

    return {
        "policy_loss": total_policy_loss / max(1, n_batches),
        "value_loss": total_value_loss / max(1, n_batches),
        "entropy": total_entropy / max(1, n_batches),
    }


# ======================== Training ========================

def train(env_name: str = "CartPole-v1", save_path: Path = None,
          max_episodes: int = MAX_EPISODES) -> ActorCritic:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    random.seed(SEED)

    env = gym.make(env_name)
    state_dim = env.observation_space.shape[0]
    num_actions = env.action_space.n
    print(f"[env] {env_name} state_dim={state_dim} num_actions={num_actions}")

    ac = ActorCritic(state_dim, num_actions)
    opt_actor = optim.Adam(ac.actor.parameters(), lr=LR_ACTOR)
    # 让 critic 跟 shared 也训练
    opt_shared = optim.Adam(list(ac.shared.parameters()) + list(ac.critic.parameters()), lr=LR_CRITIC)

    recent_returns = deque(maxlen=100)
    best_avg = -float("inf")
    start = time.time()
    ep = 0

    while ep < max_episodes:
        # 收集一个 rollout (ROLLOUT_LEN 步)
        buffer = RolloutBuffer()
        s, _ = env.reset(seed=SEED + ep)
        ep_return = 0.0
        ep_steps = 0

        for t in range(ROLLOUT_LEN):
            a, lp, v = ac.get_action(s)
            s_next, r, terminated, truncated, _ = env.step(a)
            done = terminated or truncated
            buffer.push(s, a, lp, r, v, done)
            s = s_next
            ep_return += r
            ep_steps += 1
            if done:
                ep += 1
                recent_returns.append(ep_return)
                # 重新 reset
                s, _ = env.reset(seed=SEED + ep)

        # Bootstrap value for last state
        if not done:
            with torch.no_grad():
                _, last_v = ac.forward(torch.tensor(s, dtype=torch.float32).unsqueeze(0))
                last_v = last_v.item()
        else:
            last_v = 0.0
        buffer.values.append(last_v)  # append for GAE

        # PPO 更新
        losses = ppo_update(ac, opt_actor, opt_shared, buffer)

        # Logging
        if ep % LOG_EVERY == 0:
            avg = np.mean(recent_returns)
            elapsed = time.time() - start
            print(
                f"[ep {ep:4d}] avg100={avg:6.1f} "
                f"π={losses['policy_loss']:+.3f} V={losses['value_loss']:+.3f} "
                f"H={losses['entropy']:+.3f} t={elapsed:.1f}s"
            )
            if avg > best_avg:
                best_avg = avg
                if save_path:
                    torch.save(ac.state_dict(), save_path)
                    print(f"  ★ saved best (avg={avg:.1f}) → {save_path}")

        # Solve check
        if len(recent_returns) >= 100 and np.mean(recent_returns) >= 475:
            print(f"\n[✓] SOLVED at episode {ep} (avg100={np.mean(recent_returns):.1f})")
            if save_path:
                torch.save(ac.state_dict(), save_path)
            break

    env.close()
    return ac


def evaluate(ac: ActorCritic, env_name: str = "CartPole-v1", episodes: int = 20) -> float:
    env = gym.make(env_name)
    returns = []
    for ep in range(episodes):
        s, _ = env.reset(seed=1000 + ep)
        ep_return = 0.0
        for t in range(env.spec.max_episode_steps):
            a, _, _ = ac.get_action(s, deterministic=True)
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
    p.add_argument("--quick", action="store_true", help="快速 200 ep")
    p.add_argument("--env", default="CartPole-v1")
    args = p.parse_args()

    if args.quick:
        args.episodes = 200

    save = Path(__file__).resolve().parent.parent / "checkpoints" / "ppo_cartpole.pt"
    save.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"D4ML — PPO from scratch on {args.env}")
    print(f"  γ={GAMMA} λ={GAE_LAMBDA} clip={CLIP_EPS} lr_actor={LR_ACTOR} lr_critic={LR_CRITIC}")
    print("=" * 60)

    ac = train(args.env, save_path=save, max_episodes=args.episodes)
    print("\n--- final evaluation ---")
    evaluate(ac, args.env, episodes=20)