# -*- coding: utf-8 -*-
"""
dqn.py — Deep Q-Network (DQN) implementation from scratch (PyTorch + gymnasium)

D4ML 课基础 RL 项目: 跑通 CartPole-v1 经典控制任务
- 不用 Stable Baselines 3 (依赖重), 纯手写 DQN
- Intel Iris Xe 集显可用 (PyTorch CPU 模式, 1-2 TFLOPS)
- CartPole 状态 4 维, 动作 2 离散 - 最简单 RL 入门任务
- 目标: 500 回合平均奖励 ≥ 475 (满分 500, 任务解决标准)
"""
import os
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


# ======================== Hyperparameters ========================

SEED = 42
LR = 1e-3                  # learning rate
GAMMA = 0.99               # discount factor
BATCH_SIZE = 64
BUFFER_SIZE = 10_000       # replay buffer
EPS_START = 1.0            # epsilon greedy start (100% random)
EPS_END = 0.05             # epsilon greedy end (5% random)
EPS_DECAY = 0.995          # per-episode multiplicative decay
TARGET_UPDATE = 10          # episodes between target net hard update
HIDDEN = 128               # hidden layer size
MAX_EPISODES = 600          # training cap (CartPole solves by ~200-400 typical)
LOG_EVERY = 20


# ======================== Q-Network ========================

class QNet(nn.Module):
    """Simple MLP: state_dim -> hidden -> hidden -> num_actions"""

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


# ======================== Replay Buffer ========================

class ReplayBuffer:
    """Standard experience replay buffer (uniform random sampling)"""

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
    def __init__(self, state_dim: int, num_actions: int):
        torch.manual_seed(SEED)
        np.random.seed(SEED)
        random.seed(SEED)

        self.num_actions = num_actions
        self.policy_net = QNet(state_dim, num_actions)
        self.target_net = QNet(state_dim, num_actions)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()  # target net is inference-only

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=LR)
        self.buffer = ReplayBuffer(BUFFER_SIZE)
        self.eps = EPS_START
        self.steps = 0

    def select_action(self, state: np.ndarray) -> int:
        """epsilon-greedy action selection"""
        self.steps += 1
        if random.random() < self.eps:
            return random.randrange(self.num_actions)
        with torch.no_grad():
            s = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            q = self.policy_net(s)
            return int(q.argmax(dim=1).item())

    def train_step(self) -> float | None:
        """One gradient step. Returns loss (or None if buffer too small)."""
        if len(self.buffer) < BATCH_SIZE:
            return None
        s, a, r, s_next, done = self.buffer.sample(BATCH_SIZE)

        # Q(s, a) from policy net
        q_pred = self.policy_net(s).gather(1, a.unsqueeze(1)).squeeze(1)

        # Target: r + γ * max_a Q_target(s', a) * (1 - done)
        with torch.no_grad():
            q_next = self.target_net(s_next).max(dim=1)[0]
            q_target = r + GAMMA * q_next * (1.0 - done)

        loss = F.smooth_l1_loss(q_pred, q_target)  # Huber loss
        self.optimizer.zero_grad()
        loss.backward()
        # gradient clipping for stability
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), 10.0)
        self.optimizer.step()
        return float(loss.item())

    def update_target(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def decay_eps(self):
        self.eps = max(EPS_END, self.eps * EPS_DECAY)


# ======================== Training ========================

def train(env_name: str = "CartPole-v1", save_path: Path = None) -> DQNAgent:
    """Train DQN on env, save best model to save_path."""
    env = gym.make(env_name)
    state_dim = env.observation_space.shape[0]
    num_actions = env.action_space.n
    print(f"[env] {env_name} state_dim={state_dim} num_actions={num_actions}")

    agent = DQNAgent(state_dim, num_actions)
    recent_returns = deque(maxlen=100)  # for moving average
    best_avg = -float("inf")
    start = time.time()

    for ep in range(1, MAX_EPISODES + 1):
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

        # Logging
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
                    print(f"  ★ saved best model (avg={avg:.1f}) to {save_path}")

        # CartPole 解决标准: 100 episode 平均 ≥ 475
        if len(recent_returns) >= 100 and np.mean(recent_returns) >= 475:
            print(f"\n[✓] SOLVED at episode {ep} (avg100={np.mean(recent_returns):.1f})")
            if save_path:
                torch.save(agent.policy_net.state_dict(), save_path)
            break

    env.close()
    return agent


def evaluate(agent: DQNAgent, env_name: str = "CartPole-v1", episodes: int = 20) -> float:
    """Evaluate trained agent (deterministic, epsilon=0)."""
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


if __name__ == "__main__":
    save = Path(__file__).resolve().parent.parent / "checkpoints" / "dqn_cartpole.pt"
    save.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("D4ML — DQN from scratch on CartPole-v1")
    print("=" * 60)
    agent = train("CartPole-v1", save_path=save)
    print("\n--- final evaluation ---")
    evaluate(agent, "CartPole-v1", episodes=20)