# -*- coding: utf-8 -*-
"""eval_sac.py — 评估已保存的 SAC checkpoint"""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import torch
import numpy as np
import gymnasium as gym
from sac import SACAgent, evaluate


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

    agent = SACAgent(state_dim, num_actions)
    state = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    agent.actor.load_state_dict(state["actor"])
    agent.q1.load_state_dict(state["q1"])
    agent.q2.load_state_dict(state["q2"])
    agent.log_alpha = state["log_alpha"]
    agent.actor.eval()
    agent.q1.eval()
    agent.q2.eval()

    print(f"Loaded: {args.checkpoint}")
    print(f"  alpha = {agent.alpha.item():.3f}")
    print(f"  log_alpha = {agent.log_alpha.item():.3f}")
    evaluate(agent, args.env, args.episodes)


if __name__ == "__main__":
    main()