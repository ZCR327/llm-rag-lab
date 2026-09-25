# 24306 设计演进: v2 → v3 → v3.5 → v5 (完整对比表)

> RAG 专答 "v2→v5 砍什么, 为什么砍" 用的对比表
> 9.13 凌晨 brainstorm → 9.15 砍光到 v5.5 极简 跨 4 天决策
> 来源: backups/initial_idea.md.* 历代版本 + 当前 v5.5

## 1. 设计目标 (跨版本一致)

- **赛季**: BIOBUZZ 2026-2027
- **核心动作**: AUTO 30s 装 4 POLLEN → 触发 HIVE TIP 翻倒 → 28 分
- **电机预算**: REV Control Hub 8 motor 限制 (不升级 REV v2)
- **尺寸**: 18×18×18 inch

## 2. v2 → v3.5 → v5 完整对比

| 子系统 | **v2** (8 motor + 0 servo) | **v3.5** (8 motor + 2 servo) | **v5** (6 motor + 0 servo) | 砍原因 |
|---|---|---|---|---|
| 4 drive base | ✅ 4 motor | ✅ 4 motor | ✅ 4 motor | 必保留 |
| **左 intake** (POLLEN) | ✅ 1 motor | ✅ 1 motor | ❌ **砍** | 8 motor 卡线 + POLLEN 不需 intake (4 球启动装载) |
| **右 intake** (NECTAR) | ✅ 1 motor | ✅ 1 motor | ❌ **砍** | 同上 + v5 不用 NECTAR |
| **Transfer** (球路拨片) | ✅ 1 motor | ❌ 改 servo | ❌ **砍** | 改 v3.5 用了 1 servo 摆动拨片, v5 完全不要 transfer (重力喂球) |
| **Flywheel** (发射) | ✅ 1 motor | ✅ 1 motor | ✅ 2 motor (双电机共驱) | 必保留, v5 改双电机力矩翻倍 |
| **Elevator** (升降) | ✅ 1 motor + 丝杠 | ✅ 1 motor + 丝杠 | ❌ **砍** | v5 改远射到 HIVE, 不需举到 HIVE 顶部 |
| 1 servo (球路切换) | — | ✅ 1 servo | ❌ **砍** | transfer 整个砍了 |
| 1 servo (TIP 释放) | — | ✅ 1 servo | ❌ **砍** | HIVE 自动翻倒, 不需挡块释放 |
| **DC motor 合计** | **8** ✅ | **8** ✅ | **6** ✅ 砍 2 | — |
| **servo 合计** | 0 | 2 | 0 | — |

## 3. 关键设计决策时间线

| 时间 | 决策 | 关键变化 |
|---|---|---|
| 9.13 凌晨 | brainstorm: 双 intake + 单发射 + 升降送 tip | 3 种子机制 |
| 9.13 10:55 | **A 方案**: transfer 改 servo 摆动拨片 | 8 motor 卡线, 0 余量, **不升 REV v2** |
| 9.13 17:55 | **v3 决策**: 双 intake 砍光 | POLLEN 爪子直接抓地, NECTAR intake 反转推 |
| 9.13 17:59 | **v3.5 决策**: Flywheel 改双电机驱动 | POLLEN 路径 = 爪子 → 升降 → 双电机飞轮远射 |
| 9.13 20:35 | **v5 决策**: 极简化 | 砍爪子/升降/滑轮组/NECTAR intake/intake 反推/TIP 释放 servo |
| 9.15 00:15 | **v5.5 决策**: 跷跷板累积机制修正 | 翻 1 次需 8 POLLEN (或 6 NECTAR), AUTO 30s 装 4 POLLEN 触发 1 次翻倒 = 28 分 |

## 4. 砍子系统详细原因

### 砍 左/右 intake
- **v2 用途**: POLLEN/NECTAR 从场地地面吸入机器人
- **砍原因**: 
  1. v5 改"启动装载"策略 — 4 POLLEN 在比赛开始前就装进机器人, 不需要 intake 抓地面
  2. v5 不用 NECTAR, 砍右 intake
  3. 省 2 motor 给核心动作 (flywheel 双电机)

### 砍 Transfer (球路拨片)
- **v2 用途**: 1 motor + 传送带把球从 intake 推到 flywheel
- **v3.5 修法**: 改 1 servo 摆动拨片 (不占 motor)
- **v5 砍原因**:
  1. 启动装载 4 POLLEN 后, 球靠**重力自动滑入飞轮** (机器人装载角度倾斜)
  2. 不需要中间传送, 砍 1 motor (或 servo)
  3. 简化控制 + 减重 + 减复杂度

### 砍 Elevator (升降)
- **v2 用途**: 1 motor + 丝杠, 把球举到 HIVE 顶部 CELL 触发 TIP
- **v5 改法**: 双电机飞轮**远射**到 HIVE FLOWER CELL, 球落入
- **砍原因**:
  1. 远射比举升快 (1.5s vs 3-4s)
  2. 远射精度靠瞄准 + PID, 不靠机械精度
  3. 升降行程 ≥ 30-40cm, 机构复杂 + 易卡
  4. 省 1 motor 给 flywheel 双电机

### 砍 Servo (球路切换 + TIP 释放)
- **v3.5 用途**: 2 servo 解决 8 motor 卡线
- **v5 砍原因**:
  1. 整条 transfer 链路砍了, 球路切换 servo 没用了
  2. HIVE 是**双稳态跷跷板**, 装球到阈值 (8 POLLEN) 自动翻倒, **不需挡块释放 servo**
  3. 0 servo 设计 — 最简, 0 故障点

### Flywheel 从 1 motor → 2 motor (反着砍)
- **v2**: 1 motor + 飞轮, 远射力矩不够
- **v5**: 2 motor **共驱 1 飞轮** — 力矩翻倍, RPM 高, 远射精度高
- **不砍原因**: 这是核心执行器, 唯一保留的"非 drive" 子系统
- **电机分配**: M0 + M4 共驱 1 飞轮

## 5. v5 最终设计骨架 (BIOBUZZ 实战)

```
[机器人底盘 18×18×18 in]
  ├─ 4 drive (M6-M9) — 4 motor, 必用
  └─ 2 flywheel (M0, M4 双电机共驱 1 飞轮) — 2 motor
        ├─ 启动装载 4 POLLEN (装载角度倾斜, 球靠重力滑入飞轮)
        └─ 双电机加速 1.5s → 远射 HIVE FLOWER CELL → 球落入 HIVE
              ↓
        8 球装满 FLOWER CELL → 球重力累计 → HIVE pivot 翻倒
              ↓
        触发 TIP (+20 分) → 双稳态切换
```

**0 servo, 0 intake, 0 elevator** — 极简设计, 0 故障点

## 6. 估分修正 (V0.9 规则确认后)

- 修正前 (初版): 85 分
- 修正后 (v5.5 + V0.9 翻倒阈值 = 8 POLLEN):
  - AUTO 30s 装 4 POLLEN → 触发 1 次翻倒 = 28 分
  - 翻 1 次 = 20 分 + FLOWER POLLEN 8 = 28 分
  - 装 4 POLLEN 翻 1 次后 = 22 分 (20 + 1 球 × 2)
  - 剩 7 球不重复计 = 14 分
  - **一场极限 82 分** (翻 2 次 + 16 POLLEN + PARK + AUTO 停靠)

## 7. 设计哲学 (从 v2→v5 学到的)

1. **复杂度是头号敌人** — 8 motor 卡线 = 故障点 8 个, 6 motor 反而更稳
2. **极简比"功能多"重要** — 砍掉 60% 子系统, 反而估分更高 (28 vs 估 14)
3. **重力是最便宜的执行器** — 球从装载角度滑入飞轮, 不需 servo/intake
4. **双稳态 HIVE 是设计红利** — 装 8 球自动翻, 不需复杂释放机构
5. **电机数 = 可靠性** — 留 2 motor 余量, 比"省 1 motor 升 REV v2"重要

## 8. 设计演进 vs 比赛准备 (2026 9-12 月时间线)

| 月份 | 目标 | 关键交付 |
|---|---|---|
| 9 | 设计冻结 + kickoff 老师聊 | v5.5 final, 19606 老师访谈 |
| 10 | 加工 + 装配 + 接线 | 实物, 静态测试 |
| 11 | 编程 + 单元测试 | AUTO 9→2 路径跑通 |
| 12 | 联调 + 远射瞄准 | 整场 AUTO+TELEOP, 估分 28+ |
| 2027.1 | 地区赛 | 检验 |
| 2027.2 | 州赛 / 国赛 | 冲再进世锦赛 |