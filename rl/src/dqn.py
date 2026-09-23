# -*- coding: utf-8 -*-
"""
dqn.py — DQN + Dueling DQN from scratch (PyTorch + gymnasium)

D4ML 课程项目 - 调优版 (v0.2):
- 调优超参: EPS_DECAY 0.995→0.99, BUFFER 10K→50K, MAX_EP 600→2000
- 加 Dueling DQN 架构 (Q = V(s) + A(s,a) - sample efficiency ↑)
- 同一文件, 切换 --dueling 启用 Dueling

用法:
  python src/dqn.py                  # 默认 DQN + 调优超参
  python src/dqn.py --dueling        # Dueling DQN
  python src/dqn.py --quick          # 快速测试 (100 ep)
"""
import os
import sys
import argparse
import random
import time
from collections import deque
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import gymnasium as gym


# ======================== Hyperparameters (v0.2 tuned) ========================

SEED = 42
LR = 1e-3                  # learning rate
GAMMA = 0.99               # discount factor
BATCH_SIZE = 128           # 64 → 128 (more stable gradients)
BUFFER_SIZE = 50_000      # 10K → 50K (more diverse replay)
EPS_START = 1.0
EPS_END = 0.05
EPS_DECAY = 0.99           # 0.995 → 0.99 (slower decay, explore longer)
TARGET_UPDATE = 5          # 10 → 5 (faster target sync)
HIDDEN = 128
MAX_EPISODES = 2000        # 600 → 2000 (CPU 10 min, GPU <1 min)
LOG_EVERY = 25


# ======================== Networks ========================

class QNet(nn.Module):
    """Standard DQN: state_dim -> hidden -> hidden -> num_actions"""

    def __init__(self, state_dim: int, num_actions: int, hidden: int = HIDDEN):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, num_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class DuelingQNet(nn.Module):
    """Dueling DQN: Q(s,a) = V(s) + (A(s,a) - mean_a A(s,a))

    拆分 value 和 advantage, 学习效率更高 (尤其 action 空间大时)
    """

    def __init__(self, state_dim: int, num_actions: int, hidden: int = HIDDEN):
        super().__init__()
        # 共享特征层
        self.feature = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
        )
        # Value stream: V(s) 标量
        self.value_stream = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),  # V(s) 一个数
        )
        # Advantage stream: A(s,a) 每个动作一个数
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, num_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.feature(x)
        value = self.value_stream(feat)              # (B, 1)
        advantage = self.advantage_stream(feat)      # (B, num_actions)
        # 中心化: A - mean(A) 避免 V 和 A 唯一性歧义
        q = value + (advantage - advantage.mean(dim=1, keepdim=True))
        return q


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


# ======================== DQN Agent ========================

class DQNAgent:
    def __init__(self, state_dim: int, num_actions: int, dueling: bool = False):
        torch.manual_seed(SEED)
        np.random.seed(SEED)
        random.seed(SEED)

        NetCls = DuelingQNet if dueling else QNet
        self.num_actions = num_actions
        self.policy_net = NetCls(state_dim, num_actions)
        self.target_net = NetCls(state_dim, num_actions)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=LR)
        self.buffer = ReplayBuffer(BUFFER_SIZE)
        self.eps = EPS_START
        self.steps = 0
        self.dueling = dueling

    def select_action(self, state: np.ndarray) -> int:
        self.steps += 1
        if random.random() < self.eps:
            return random.randrange(self.num_actions)
        with torch.no_grad():
            s = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            q = self.policy_net(s)
            return int(q.argmax(dim=1).item())

    def train_step(self) -> float | None:
        if len(self.buffer) < BATCH_SIZE:
            return None
        s, a, r, s_next, done = self.buffer.sample(BATCH_SIZE)

        q_pred = self.policy_net(s).gather(1, a.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            q_next = self.target_net(s_next).max(dim=1)[0]
            q_target = r + GAMMA * q_next * (1.0 - done)

        loss = F.smooth_l1_loss(q_pred, q_target)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), 10.0)
        self.optimizer.step()
        return float(loss.item())

    def update_target(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def decay_eps(self):
        self.eps = max(EPS_END, self.eps * EPS_DECAY)


# ======================== Training ========================

def train(env_name: str = "CartPole-v1", save_path: Path = None,
         dueling: bool = False, max_episodes: int = MAX_EPISODES) -> DQNAgent:
    env = gym.make(env_name)
    state_dim = env.observation_space.shape[0]
    num_actions = env.action_space.n
    arch = "Dueling DQN" if dueling else "DQN"
    print(f"[env] {env_name} state_dim={state_dim} num_actions={num_actions} arch={arch}")

    agent = DQNAgent(state_dim, num_actions, dueling=dueling)
    recent_returns = deque(maxlen=100)
    best_avg = -float("inf")
    start = time.time()

    for ep in range(1, max_episodes + 1):
        s, _ = env.reset(seed=SEED + ep)
        ep_return = 0.0
        ep_loss_sum = 0.0
        ep_loss_n = 0

        for t in range(env.spec.max_episode_steps):
            a = agent.select_action(s)
            s_next, r, terminated, truncated, _ = env.step(a)
            done = terminated or truncated
            agent.buffer.push(s, a, r, s_next, float(done))
            s = s_next
            ep_return += r

            loss = agent.train_step()
            if loss is not None:
                ep_loss_sum += loss
                ep_loss_n += 1

            if done:
                break

        agent.decay_eps()
        recent_returns.append(ep_return)

        if ep % TARGET_UPDATE == 0:
            agent.update_target()

        if ep % LOG_EVERY == 0:
            avg = np.mean(recent_returns)
            elapsed = time.time() - start
            avg_loss = ep_loss_sum / max(1, ep_loss_n)
            print(
                f"[ep {ep:4d}] return={ep_return:6.1f} avg100={avg:6.1f} "
                f"eps={agent.eps:.3f} loss={avg_loss:.3f} t={elapsed:.1f}s"
            )
            if avg > best_avg:
                best_avg = avg
                if save_path:
                    torch.save(agent.policy_net.state_dict(), save_path)
                    print(f"  ★ saved best (avg={avg:.1f}) → {save_path}")

        # CartPole 解决: 100 episode 平均 ≥ 475
        if len(recent_returns) >= 100 and np.mean(recent_returns) >= 475:
            print(f"\n[✓] SOLVED at episode {ep} (avg100={np.mean(recent_returns):.1f})")
            if save_path:
                torch.save(agent.policy_net.state_dict(), save_path)
            break

    env.close()
    return agent


def evaluate(agent: DQNAgent, env_name: str = "CartPole-v1", episodes: int = 20) -> float:
    env = gym.make(env_name)
    returns = []
    for ep in range(episodes):
        s, _ = env.reset(seed=1000 + ep)
        ep_return = 0.0
        for t in range(env.spec.max_episode_steps):
            with torch.no_grad():
                q = agent.policy_net(torch.tensor(s, dtype=torch.float32).unsqueeze(0))
                a = int(q.argmax(dim=1).item())
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
    p.add_argument("--dueling", action="store_true", help="用 Dueling DQN 架构")
    p.add_argument("--quick", action="store_true", help="快速测试 (100 回合)")
    p.add_argument("--episodes", type=int, default=MAX_EPISODES, help=f"最大回合数 (默认 {MAX_EPISODES})")
    p.add_argument("--env", default="CartPole-v1", help="gymnasium 环境名")
    args = p.parse_args()

    if args.quick:
        args.episodes = 100
        EPS_DECAY = 0.99  # still slow decay for quick test

    save_name = "dqn_dueling_cartpole.pt" if args.dueling else "dqn_cartpole.pt"
    save = Path(__file__).resolve().parent.parent / "checkpoints" / save_name
    save.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    arch_name = "Dueling DQN" if args.dueling else "DQN"
    print(f"D4ML — {arch_name} (v0.2 tuned) on {args.env}")
    print(f"  EPS_DECAY={EPS_DECAY} BUFFER={BUFFER_SIZE} BATCH={BATCH_SIZE} TARGET_UPDATE={TARGET_UPDATE}")
    print("=" * 60)

    agent = train(args.env, save_path=save, dueling=args.dueling, max_episodes=args.episodes)
    print("\n--- final evaluation ---")
    evaluate(agent, args.env, episodes=20)