# RL (D4ML 课程项目)

D4ML 课基础 RL 项目 - Deep Q-Network (DQN) from scratch on CartPole-v1。

## 快速跑

```bash
pip install torch gymnasium  # 已有
python src/dqn.py
```

预期: 600 回合内训练 (CPU ~3 min)，100 回合平均奖励最高 ~220，solved 阈值 475。

## 当前结果 (2026-09-23)

```
ep 440 best: avg100=223.5
ep 600: avg100=103.3
eval (20 eps): avg=100.0, min=83, max=152
```

**未 solve**（< 475）。原因：CPU 跑 600 回合不够，epsilon 衰减太快。

## 调优方向

1. **更大训练** (PyTorch GPU 加速 / 2000+ 回合)
2. **超参调整**:
   - `EPS_DECAY`: 0.995 → 0.99 (更慢衰减, 探索更久)
   - `BUFFER_SIZE`: 10K → 50K (更多 replay 经验)
   - `BATCH_SIZE`: 64 → 128
3. **网络结构**: 加 dueling network (Dueling DQN)
4. **改进**:
   - Double DQN (解耦动作选择 + 价值评估)
   - Prioritized Experience Replay
   - Noisy Nets (替代 epsilon-greedy)

## 进阶方向 (后续)

- [ ] D4ML 课提交: 把 DQN 代码 + 训练曲线 + 评估报告打成报告
- [ ] RL 串 FTC 路径规划 (Bézier + RL 决策)
- [ ] PPO / SAC 算法 (policy gradient 方向)

## 文件

```
rl/
├── src/dqn.py            # DQN 算法实现 (~250 行, PyTorch + gymnasium)
├── checkpoints/          # 保存的训练模型
│   └── dqn_cartpole.pt   # best model (avg100=223.5)
├── logs/                 # (空, 预留训练日志)
└── README.md             # 本文件
```

## D4ML 课报告草稿要点

1. **算法**: DQN (Deep Q-Network) - value-based off-policy
2. **环境**: CartPole-v1 (4-dim state, 2-dim action, max 500 step)
3. **网络**: 2 hidden layer MLP (4 → 128 → 128 → 2)
4. **关键技术**:
   - Experience replay (10K buffer, uniform sampling)
   - Target network (hard update every 10 episodes)
   - ε-greedy exploration (1.0 → 0.05, decay 0.995)
   - Huber loss (smooth L1, 比 MSE 稳)
   - Gradient clipping (max norm 10.0)
5. **结果**: best avg100=223.5 (未达 475 solve 阈值, 训练时间限制)
6. **讨论**: CPU 训练瓶颈 + 调参经验

## 引用

- Mnih et al. (2015). Human-level control through deep reinforcement learning. Nature.
- OpenAI Spinning Up — DQN tutorial
- PyTorch DQN tutorial
- Stable Baselines3 (for future reference)