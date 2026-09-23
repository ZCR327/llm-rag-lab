# -*- coding: utf-8 -*-
"""eval_dqn.py — 评估已保存的 DQN / Dueling DQN checkpoint"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import torch
import numpy as np
import gymnasium as gym
from dqn import QNet, DuelingQNet, evaluate, SEED


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("checkpoint", help=".pt 路径")
    p.add_argument("--dueling", action="store_true")
    p.add_argument("--episodes", type=int, default=20)
    p.add_argument("--env", default="CartPole-v1")
    args = p.parse_args()

    env = gym.make(args.env)
    state_dim = env.observation_space.shape[0]
    num_actions = env.action_space.n

    NetCls = DuelingQNet if args.dueling else QNet
    net = NetCls(state_dim, num_actions)
    state = torch.load(args.checkpoint, map_location="cpu")
    net.load_state_dict(state)
    net.eval()
    env.close()

    print(f"Loaded: {args.checkpoint} (arch={'Dueling' if args.dueling else 'DQN'})")
    env = gym.make(args.env)
    returns = []
    for ep in range(args.episodes):
        s, _ = env.reset(seed=1000 + ep)
        ep_return = 0.0
        for t in range(env.spec.max_episode_steps):
            with torch.no_grad():
                q = net(torch.tensor(s, dtype=torch.float32).unsqueeze(0))
                a = int(q.argmax(dim=1).item())
            s, r, terminated, truncated, _ = env.step(a)
            ep_return += r
            if terminated or truncated:
                break
        returns.append(ep_return)
    env.close()

    avg = np.mean(returns)
    print(f"[eval] {args.env} over {args.episodes} eps: avg={avg:.1f}, min={min(returns):.0f}, max={max(returns):.0f}")
    return avg


if __name__ == "__main__":
    main()