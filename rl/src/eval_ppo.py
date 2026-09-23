# -*- coding: utf-8 -*-
"""eval_ppo.py — 评估已保存的 PPO checkpoint"""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import torch
import numpy as np
import gymnasium as gym
from ppo import ActorCritic, evaluate


def main():
    p = argparse.ArgumentParser()
    p.add_argument("checkpoint", help=".pt 路径")
    p.add_argument("--episodes", type=int, default=20)
    p.add_argument("--env", default="CartPole-v1")
    args = p.parse_args()

    env = gym.make(args.env)
    state_dim = env.observation_space.shape[0]
    num_actions = env.action_space.n
    env.close()

    ac = ActorCritic(state_dim, num_actions)
    state = torch.load(args.checkpoint, map_location="cpu")
    ac.load_state_dict(state)
    ac.eval()

    print(f"Loaded: {args.checkpoint}")
    evaluate(ac, args.env, args.episodes)


if __name__ == "__main__":
    main()