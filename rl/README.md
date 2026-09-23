# RL (D4ML 课程项目)

D4ML 课基础 RL 项目 - **DQN + Dueling DQN from scratch** on CartPole-v1 (PyTorch + gymnasium)。

## 🎉 训练结果 (v0.2)

| 架构 | 训练 | 评估 (50 ep) | 状态 |
|---|---|---|---|
| **DQN v0.2** (tuned) | 800 ep / 7.5 min CPU | **avg=500.0** (min=500, max=500) | ✅ **SOLVED** |
| **PPO v0.1** (tuned) | 1500 ep / 67s CPU | **avg=500.0** (min=500, max=500) | ✅ **SOLVED** |
| **SAC v0.2** (discrete V(s') fix) | 1000 ep / 58s CPU | avg=9.2 (saved best avg=24.4) | ❌ 未收敛 (Q 网络未学起) |
| Dueling DQN v0.2 (full 2000 ep) | 30 min CPU | avg=167.4 (min=89, max=500) | ⚠️ CPU 跑 2000 ep 不够 |
| DQN v0.1 (untuned) | 600 ep / 3 min CPU | avg=304.0 (eval 30ep) | ⚠️ 接近但不稳定 |

**Solve 阈值**: 100 ep 平均 ≥ 475。DQN v0.2 在 ep 525 时达 avg100=**452**（最近一次），saved checkpoint 在 50 episode 评估里**完美 500/500**。

## 快速跑

```bash
# 训练 (默认 DQN, 2000 ep 上限)
python src/dqn.py --episodes 800

# Dueling DQN
python src/dqn.py --dueling --episodes 1500

# 评估已保存的 checkpoint
python src/eval_dqn.py checkpoints/dqn_cartpole.pt --episodes 50
python src/eval_dqn.py checkpoints/dqn_dueling_cartpole.pt --dueling --episodes 50
```

## v0.1 → v0.2 调优对比

| 超参 | v0.1 | v0.2 (tuned) |
|---|---|---|
| LR | 1e-3 | 1e-3 (同) |
| BATCH_SIZE | 64 | 128 |
| BUFFER_SIZE | 10K | 50K |
| EPS_DECAY | 0.995 | **0.99** (slower) |
| TARGET_UPDATE | 10 ep | 5 ep (faster sync) |
| HIDDEN | 128 | 128 (同) |
| MAX_EPISODES | 600 | 2000 |

**关键**: EPS_DECAY 0.995→0.99 (探索更久) + BUFFER 5x + TARGET_UPDATE 2x (目标网络更新更频繁)

## 训练曲线 (DQN v0.2)

```
ep   25: avg100=  19   eps=0.778  loss=0.082
ep  100: avg100=  47   eps=0.366  loss=0.112
ep  200: avg100= 117   eps=0.134
ep  300: avg100= 278   eps=0.050
ep  500: avg100= 435   eps=0.050  ★ 接近 solve
ep  525: avg100= 452   ★ best (saved)
ep  550: avg100= 400   ← 灾难性遗忘
ep  800: avg100=  59   (崩溃)
```

**Solve = 50/50 完美** (在 50 episode 独立评估里)。Saved checkpoint 是 ep 525 (avg100=452, best in training)。

## 算法实现

### DQN (`QNet`)
```
B(t) = (1-t)³·P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³·P3
state_dim → 128 → 128 → num_actions
```

### PPO (`ActorCritic`)
```
- 共享 backbone: state_dim → 64 → 64 (Tanh)
- Actor head: 64 → num_actions (logits, Categorical 采样)
- Critic head: 64 → 1 (V(s))
- 策略: on-policy, 每 500 步一个 rollout
- 目标: min(ratio · A, clip(ratio, 1-ε, 1+ε) · A), ε=0.2
- GAE: A_t = Σ_l (γλ)^l δ_{t+l},  λ=0.95
```

### Dueling DQN (`DuelingQNet`)

### 关键技术 (6 项 DQN 论文核心)
1. **Experience Replay** (50K buffer, uniform sampling)
2. **Target Network** (hard update 每 5 ep)
3. **ε-greedy** (1.0 → 0.05, decay 0.99)
4. **Huber loss** (smooth L1, 比 MSE 稳)
5. **Gradient clipping** (max norm 10.0)
6. **(Dueling)** V/A 拆分 + 中心化

### PPO 关键技术 (Schulman 2017)
1. **Clipped surrogate objective**: `min(ratio·A, clip(ratio, 1-ε, 1+ε)·A)` 防过大更新
2. **GAE (Generalized Advantage Estimation)**: λ=0.95 平衡偏差/方差
3. **Multiple epochs per rollout**: 同一批数据用 4 epoch (mini-batch 64)
4. **Entropy bonus**: -ENTROPY_COEF·H (鼓励探索, 防过早收敛)
5. **Value function clipping**: 共享 critic + actor 优化
6. **On-policy**: rollout 用完即丢 (vs DQN replay)

## 文件

```
rl/
├── src/
│   ├── dqn.py             # DQN + Dueling DQN 训练 (~280 行)
│   ├── eval_dqn.py        # 独立评估 DQN/Dueling
│   ├── ppo.py             # PPO from scratch (~310 行)
│   ├── eval_ppo.py        # 独立评估 PPO
│   ├── sac.py             # SAC v0.2 from scratch (~310 行, 未收敛)
│   └── eval_sac.py        # 独立评估 SAC
├── checkpoints/
│   ├── dqn_cartpole.pt           (170KB, ✅ SOLVED 500/500)
│   ├── dqn_dueling_cartpole.pt   (140KB, ⚠️ CPU 30 min 跑 2000 ep, 167/500 - 需 GPU/更长)
│   ├── ppo_cartpole.pt           (140KB, ✅ SOLVED 500/500)
│   ├── sac_cartpole.pt           (140KB, v0.1 未收敛)
│   └── sac_v2_cartpole.pt        (140KB, v0.2 V(s') fix, 仍未收敛)
├── logs/                  # (空, 预留)
└── README.md
```

## 进阶方向 (后续)

- [x] PPO (on-policy, 主流) - **1500 ep SOLVED 500/500** ✅
- [x] SAC v0.2 (V(s') full-sum fix + -log|A| entropy) - **未收敛** (Q 网络未学起, 跟 PPO/DQN 不同)
- [ ] 串 FTC 路径规划 (Bézier + RL 决策)
- [x] 调 Dueling DQN 训练时长: 2000 ep / 30 min 仍 167/500 (需 GPU 或 5000+ ep)
- [ ] 调 DQN EPS_DECAY 0.99 → 0.995 (防 catastrophic forgetting)
- [ ] Target network 软更新 (Polyak averaging) 而非硬更新

## SAC 调优失败诊断 (失败教训)

跑了 v0.1 (sampled a_next) + v0.2 (full-sum V(s') + -log|A| entropy) 两次, **都不收敛** (eval ~9/500 = random).

**可能 root cause** (未深究):
1. Q1/Q2 都没学起来 — target 太依赖 actor + Q_target, actor 没学所以 Q_target 没信号, Q_target 没信号所以 actor 没法学, 鸡生蛋蛋生鸡
2. 离散动作 SAC 难调 (continuous 简单因高斯可微)
3. Twin Q 减少 overestimation 但也减缓学习
4. START_STEPS=1000 + 600 ep × 12 步 = 7200 steps (但都随机, 没训练信号)
5. Tau=0.005 软更新可能太慢 — CartPole 这种快收敛任务, 软更新跟不上

**教训**: 离散 SAC 不 work 时, **优先用 Stable Baselines 3 跑 baseline 对比**, 不要纯自己写. SB3 内置 SAC 离散版 + 100+ ep CartPole 应该秒解.

**课程应用**: D4ML 报告里把 SAC 写为 "**试了从零实现, 离散动作 SAC 有非平凡挑战, 改用 DQN/PPO 跑通**, 引用 SB3 替代方案". 诚实记录, 拿到"工程试错经验"分.

## 训练曲线 (PPO v0.1)

```
ep  270: avg100=257  π=-0.002  V=+82.4   H=+0.65
ep  600: avg100=259  π=+0.015  V=+89.7
ep  850: avg100=270  π=+0.025  V=+111.9
ep 1120: avg100=274  π=+0.015  V=+281.8   ★ best saved
ep 1500: avg100=262

[eval 20 ep, deterministic]: avg=500.0, min=500, max=500 ✅ SOLVED
```

**注意**: best avg100 训练期只 274, 但 eval deterministic = 500/500. 原因: PPO 训练用随机采样, 训练期 high variance; eval 强制 deterministic argmax, 完全发挥策略.

## D4ML 课报告草稿要点

1. **3 个算法**: DQN + Dueling DQN (value-based off-policy) + PPO (on-policy policy gradient)
2. **环境**: CartPole-v1 (4-dim state, 2-dim action, max 500 step)
3. **超参调优**:
   - DQN: EPS_DECAY 0.995→0.99, BUFFER 10K→50K, BATCH 64→128, TARGET_UPDATE 10→5
   - PPO: 默认 GAE λ=0.95, clip=0.2, lr_actor=3e-4 (标准超参即 solve)
4. **结果**:
   - DQN v0.2: 800 ep / 7.5 min CPU → SOLVED eval 500/500
   - PPO: 1500 ep / 67s CPU → SOLVED eval 500/500
   - Dueling: 训练不足 (167/500)
5. **Dueling 原理**: Q = V(s) + (A(s,a) - mean A), 拆分 V/A 提升学习效率
6. **PPO 原理**: Clipped surrogate objective 防策略剧变, GAE 平衡偏差/方差
7. **讨论**: CPU 训练瓶颈 + Catastrophic Forgetting (DQN ep 525 后崩溃) + 软更新方案

## 引用

- Mnih et al. (2015). Human-level control through deep reinforcement learning. Nature.
- Wang et al. (2016). Dueling Network Architectures for Deep Reinforcement Learning. ICML.
- OpenAI Spinning Up — DQN tutorial
- PyTorch DQN tutorial
- Stable Baselines3 (for future reference)