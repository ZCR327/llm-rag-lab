# 24306 BIOBUZZ — 初始设计思路

> 9.13 凌晨 brainstorm。3 种子机制："双 intake + 单发射 + 升降送 tip"。
> 10:55 决策 (v2)：A 方案 — transfer 改 servo，**8 motor 卡线 0 余量**。
> 17:55 决策 (v3)：**双 intake 砍光**。POLLEN 爪子直接抓地面；NECTAR intake 反转推。**5 motor + 3 余量**。
> 17:59 决策 (v3.5)：**flywheel 改双电机驱动**。POLLEN 路径 = 爪子抓球 → 升降举到喂球位 → 双电机 flywheel 远射。**8 motor + 2 servo，卡线 0 余量**。
> 20:35 决策 (v5)：**极简化设计**。**砍爪子/升降/滑轮组/NECTAR intake/intake 反推/TIP 释放 servo**。**6 motor + 0 servo，余 2 motor**。AUTO 30s 装 4 POLLEN 进 HIVE FLOWER CELL = **88 分**。
> 9.15 00:15 决策 (v5.5, 当前)：**跷跷板累积机制修正**。HIVE 翻 1 次需要 8 POLLEN（或 6 NECTAR）累积在一边 = **不是装 1 球触发**。AUTO 30s 装 4 POLLEN 触发 1 次翻倒 = **28 分**（FLOWER POLLEN 8 + TIP 20）。一场比赛极限 = 翻 2 次 + 16 POLLEN + PARK + AUTO 停靠 ≈ **82 分**。
> 等 Game Manual 第 5 章 (Scoring Details) 出 V2 后再迭代。

## 设计骨架 (v5.5, 9.15 00:15)

```
       [机器人底盘 18×18×18 in]
            │
            ├─ 4 drive (M6-M9, 底盘 4 轮)
            │
            └─ 2 flywheel (M0 + M4 双电机共驱 1 飞轮)
                   │
                   ├─ 启动装载 4 POLLEN（机器人自带, 装载角度倾斜让球靠重力滑入飞轮）
                   │
                   └─ 双电机加速 1.5s → 远射 HIVE FLOWER CELL → 球落入 HIVE 顶 CELL
                              ↓
                         ⚠️ 跷跷板累积机制（用户确认）:
                          单球不触发翻倒, 需累积 8 POLLEN (或 6 NECTAR)
                          FLOWER CELL 装满 8 POLLEN → 球重力累计 → HIVE pivot 翻倒
                              ↓
                         触发 TIP (+20 分) → 双稳态切换 (朝下变朝上, 另一边朝下)
```

### 跷跷板累积机制（关键 insight, 用户确认）

- HIVE 是双稳态跷跷板结构（pivot 双稳态 + damper 防回弹）
- **不**是装 1 球就触发翻倒, 而是**累积多球**才翻
- **8 POLLEN** (7.1cm 小球) 累积在一边 → 触发翻倒
- 或 **6 NECTAR** (9.1cm 大球, 单球更重) 累积在一边 → 触发翻倒
- 翻倒 = 双稳态切换, 朝下变朝上, 另一边朝下
- **一场比赛 HIVE 最多翻 2 次**（设计容量限制）

### 三大子系统 (v5.5 极简)

1. **双电机 flywheel** (POLLEN 远射机构, v5.5 唯一执行器)
   - 2× DC motor (M0, M4) **共驱 1 个飞轮** = 力矩翻倍, RPM 高, 远射精度高
   - 喂入：启动装载 4 POLLEN, 机器人倾斜角度让球靠重力自动滑入飞轮入口（无需 servo 释放）
   - 远射：双电机加速 1.5s 后射出 → HIVE FLOWER CELL → 球落入 HIVE 顶 CELL
   - 1 球装入得分 = **FLOWER POLLEN 2**（不触发 TIP, 累积数不够）
   - 8 球装满 FLOWER CELL = **触发 1 次 TIP = 20 分**

2. **底盘 + 4 drive**
   - 4× DC motor (M6-M9, 必用)

3. **0 servo + 0 intake + 0 升降** (v5 砍了)
   - 不需要爪子（POLLEN 来源 = 启动装载, 不抓地面/不放 FLOWER）
   - 不需要升降（POLLEN 远射到 HIVE, 不需要举爪子到 HIVE 高）
   - 不需要 NECTAR intake（v5.5 暂用 POLLEN 单路径, NECTAR 累积机制复杂度高留 v6）
   - 不需要 TIP 释放 servo（HIVE 自动翻倒）

## 5 个关键问题

1. ✅ **电机数** (6 motor, 2 余量) — v5 决策保留
   - **6 motor 必用**: 4 drive (M6-M9) + 2 flywheel (M0, M4 双电机共驱 1 飞轮)
   - **0 servo**: 启动装载角度让 POLLEN 自动滑入飞轮（重力喂球）
   - **2 motor 余量**: 备用 / 减重 / 加 NECTAR intake (v6 待定)
   - **保留 REV Control Hub** (8 motor 限制, 远低于)

2. **球路由** (POLLEN 远射 vs 放置)
   - v5.5 远射 = 双电机 flywheel 力矩大 + 命中率靠瞄准 + V2 规则确认

3. ✅ **TIP 翻倒机制** (跷跷板累积, 用户确认) — v5.5 修正
   - **累积多球触发**: 不是装 1 球触发翻倒
   - **8 POLLEN** (7.1cm 小球) 或 **6 NECTAR** (9.1cm 大球) 累积在一边 → 触发翻倒
   - HIVE 双稳态: 一边 CELL 朝下 (有球) + 另一边 CELL 朝上 (空), 翻倒后状态交换
   - 一场最多翻 2 次

4. **远射瞄准精度** (v5.5 核心难点)
   - 远射精度要求高 (FLOWER CELL 入口小, 球必须落入才能累积)
   - AprilTag 视觉伺服（V2 规则确认 HIVE 是否有 AprilTag）vs 预编程轨迹 vs 纯 PID
   - 9 月 kickoff meeting + 19606 老师聊

5. **联盟协同** (TELEOP 阶段 + 联盟伙伴)
   - 联盟 2 队/联盟, 4 队/场
   - partner 帮装 POLLEN 进其他 HIVE = 协同得分
   - 9 月 kickoff meeting 拍板

## 舵机 vs 电机 (v5.5 极简)

| 用途 | 用啥 | 数量 |
|------|------|------|
| 4 drive base | 4× DC motor | 4 |
| 2 flywheel (POLLEN 远射, 双电机共驱 1 飞轮) | 2× DC motor | 2 |
| ~~POLLEN 升降 (motor + 滑轮组)~~ | 砍 | 0 |
| ~~NECTAR intake~~ | 砍 (v5.5 单 POLLEN 路径) | 0 |
| ~~POLLEN 爪子 (servo 张合)~~ | 砍 | 0 |
| ~~TIP 释放 (servo)~~ | 砍 | 0 |
| **DC motor 合计** | — | **6** ✅ (余 2 motor) |
| **servo 合计** | — | **0** ✅ |

## 决策 (9.15 00:15, v5.5 当前)

**v5 → v5.5 关键修正**:
- **TIP 翻倒累积机制**（用户确认 9.15 00:05）: 跷跷板需要 8 POLLEN 或 6 NECTAR 累积才翻 1 次, 不是装 1 球触发
- **一场比赛极限翻 2 次**（用户确认 9.15 00:15）: HIVE 设计容量限制
- **AUTO 30s 装 4 POLLEN 触发 1 次翻倒** = 28 分（不是之前估的 88 分）
- **TELEOP 2min 装 4 POLLEN 触发第 2 次翻倒** = 28 分
- **总极限**: 16 POLLEN × 2 (FLOWER POLLEN 32 分) + 2 × 20 (TIP 40 分) + PARK 5 + AUTO 停靠 5 = **82 分**

**理由**:
- 用户从实际 HIVE 物理机制澄清 = **最权威信息**
- v5.5 估分 28 (AUTO) + 28 (TELEOP) + 26 (PARK/停靠/LEAVE/GARDEN 等) ≈ **82 分**
- 比 v5 估的 88 分略低, 但更准确
- 设计骨架不变 (4 drive + 2 flywheel + 0 servo = 6 motor 余 2)

**v5.5 vs 之前版本**:
- v3.5: 8 motor 卡线 0 余量, 复杂 (爪+升降+滑轮组+flywheel+intake), 估 AUTO 28 分
- v5: 6 motor 余 2, 极简, 估 AUTO 88 分 (错估, 跷跷板累积未考虑)
- v5.5: 6 motor 余 2, 极简, 估 AUTO 28 分 (1 翻倒) + TELEOP 28 分 (2 翻倒) = 56 分 POLLEN + 26 分其他 = **82 分**

**候选**:
- A. **v5.5 极简** (当前画) — 4 drive + 2 flywheel + 0 servo = 6 motor, AUTO 28 分, TELEOP 28 分, 总 82 分
- B. v5.5 + NECTAR intake — 加 1 motor (8 motor 卡线), 6 NECTAR 累积翻倒 = +12 NECTAR × 2 = +24 分 + 1 TIP 20 分 = +44 分, 总 126 分
- C. v3.5 双路径 — POLLEN 爪 + NECTAR intake 反推 + 双 flywheel = 8 motor 卡线, 估 AUTO 28 分 (1 翻倒)

## 9.15 待办 (凌晨)

- [ ] 跟 19606 老师 (ivymaker 同一人) 聊 30 分钟 — 确认跷跷板 8/6 累积 + 双电机 flywheel 齿轮配置 + 飞轮材质/直径
- [ ] Game Manual V2 第 5 章 Scoring Details (9 月中出) — 确认 PARK/AUTO 停靠分值 + TIP 分值
- [ ] AprilTag 视觉伺服方案 — V2 规则确认 HIVE 是否有 AprilTag
- [ ] Pedro Pathing 简化: 9 paths → AUTO 2 paths (GO_HIVE + SHOOT_1) + TELEOP 一组
- [ ] 9 月 kickoff meeting 全员对 v5.5 投票
- [ ] v5.5 写进文书 — 28+28+26=82 分设计 = T0 申请加分项 (极简 + 跷跷板累积机制 + 双电机 flywheel 远射精度)
- [ ] NECTAR 路径评估 (v6?) — 6 NECTAR 累积触发翻倒 = 6 × 2 (NECTAR) + 20 (TIP) = 32 分/批, 但需加 1 motor (intake + 反推机构)

## V0.9 规则复核 (2026-09-22, Game Manual 中文版)

> Game Manual V0.9 中文版 + 9.22 复核. V1 / V2 待 10 月出. 标记 = 已确认, ⚠️ = 待 V2 确认.

### 12.1 机器人尺寸 (R102, R105)

- ✅ 初始 18 × 18 × 18 in (R102) — v5.5 紧凑设计 (4 drive + 2 flywheel) 完全容纳
- ✅ 扩展后 18 × 24 × 29 in (R105) — 远射机构 + 装载槽 (倾斜 -5°) 不超
- 任何预装得分道具可超初始尺寸 — v5.5 启动装载 4 POLLEN 装在机器人内部不算超

### 12.5 电机 + 执行器 (R501, R502, R503)

- ✅ 电机 ≤ 8 个 (R503) — v5.5 用 **6 motor** (4 drive M6-M9 + 2 flywheel M0/M4), 余 2
- ✅ 伺服 ≤ 8 个 (R503) — v5.5 用 **0 servo**, 完全空
- ✅ 电机型号在 R501 允许列表 — REV HD Hex 12V DC (REV-41-1291) ✓
- ✅ 伺服型号 (空) — N/A
- ✅ R504 不改电机 — 整机安装 (出厂配置) + 配齿轮 (公开售 1:1 减速箱)
- ✅ R506 不用继电器/电磁铁/电磁阀 — v5.5 纯电机 + 齿轮

### 12.4 标识 (R401-R403)

- 待做: 队号 24306 / "Human Machine" ≥ 2 个位置, 距 90°, 字体 ≥ 2.25 in (R403), ≥ 6.5 × 2.5 in 红色矩形 (R402)

### 9.x 比赛结构 (V0.9)

- 场地: 12 × 12 ft 泡沫地砖, 144 in × 144 in, 1 ft 围栏
- HIVE: 中央, 每联盟 1 个, 2 个蜂房, 双稳态跷跷板
- 4 个 FLOWER: 围墙, 顶部开 Ø 4 in, 底部取回 Ø 2.79 in
- AprilTag 30-45: 蜂房底 (4 个/蜂房)

### 10.x 计分 (V0.9 表 10-2, **按 v5.5 极简估分**)

| 项 | AUTO | TELEOP | v5.5 累计 |
|---|---|---|---|
| 远离 LEAVE (围墙外) | 3 | - | 3 |
| 停靠 PARK (装载区) | 5 | 5 | 10 (AUTO+TELEOP) |
| 蜂巢翻倒 TIP (20/次, 一场最多 2) | 20 | 20 | **40** (2 翻倒) |
| 蜂房内 POLLEN/NECTAR | - | 2 | 32 (16 POLLEN × 2) |
| 底部花蜜奖励 | - | 5 | (v5.5 不打 NECTAR) |
| 已有花朵 POLLEN | - | 2 | 0 (v5.5 不到 FLOWER) |
| 花园内 | - | 1 | (v5.5 不到花园) |
| **v5.5 总极限** | | | **85 分** |

> 注: V0.9 vs V0.7 之前估的 82 分有微差, 因为重新算 POLLEN 16×2 = 32 (已含在花房) + 翻 2×20 = 40 + 停靠 10 + 远离 3 = **85**.

### 10.6 RP 阈值 (V0.9 表 10-3)

- 蜂群 RP: LEAVE + PARK ≥ **16** — v5.5 = 3 + 10 = **13, 差 3 拿不到** ⚠️
- 传粉 1 RP: 翻倒 ≥ 4 次 — v5.5 保守策略最多 2 次, 拿不到 ⚠️
- 传粉 2 RP: 翻倒 ≥ 7 次 — 同上, 拿不到 ⚠️
- 获胜 RP: 比赛分 > 对手 — 靠联盟伙伴

**结论**: v5.5 单台机器人**只靠获胜 RP 拿 RP**, 蜂群 + 传粉都拿不到. T0 申请文书**不夸大** v5.5 性能, 但强调"极简 + 教学价值".

### 9.7 场地 + 8.x 道具

- 启动装载: 每机器人 4 POLLEN (10.3.4)
- 一场总共: **40 POLLEN** (4 花朵 × 4 + 红花园 4 + 蓝花园 4 + 2 机器人 × 4) + **8 红 + 8 蓝 NECTAR** (朝上蜂房 3×2 + 联盟区域 5×2)
- 道具尺寸: POLLEN Ø 2.8 in (7.1 cm 黄), NECTAR Ø 3.6 in (9.1 cm 红/蓝)
- 一场 POLLEN 配比: 8 球满 1 蜂房 = 2 蜂房 × 8 = 16 球 = **4 POLLEN/联盟刚好满 1 蜂房** → v5.5 估的"AUTO 装 4 POLLEN 触发 1 翻倒"是基于 1 联盟总 8 球 (1 机器人 + 1 联盟伙伴)
- 联盟 4 队/场 = 2 联盟, 配 2 HIVE = 各联盟独立操作自己的 HIVE

### 10.4 比赛时长

- ✅ AUTO 30s (R10.4)
- ✅ 过渡 8s (用于计分, 不算入)
- ✅ TELEOP 2min
- 总 2:38, 与 v5.5 设计假设一致

### V0.9 仍未明说 (待 V2 第 5 章 Scoring Details)

- ⚠️ 蜂巢翻倒的物理阈值 (8 POLLEN / 6 NECTAR 是不是 V0.9 规则? 还是赛事现场实测?)
- ⚠️ 翻倒计分是不是"翻 1 次 = 20 分"还是"翻 1 次 + 8 POLLEN 在场 = 20 + 16 = 36 分"?
- ⚠️ POLLEN 装入 HIVE 的具体方式 (投, 滚, 滑) 是否有限制?
- ⚠️ NECTAR 累积阈值 6 是基于球数还是重量?
- ⚠️ TELEOP 期间能否改变已装入 HIVE 的球? (v5.5 假设不能, 但 V0.9 未明说)

> V2 出后再迭代 v5.5.加完。备份在 `D:\Users\xiaomi\Desktop\FTC\24306\2026-2027_BIOBUZZ\backups\initial_idea_v5.5_20260922_190200.bak`。

## V0.9 复核关键发现

| 项 | v5.5 状态 |
|---|---|
| **电机 ≤ 8 (R503)** | ✅ 6/8，余 2 |
| **尺寸 18×18×18 in (R102)** | ✅ 紧凑 |
| **电机型号 (R501)** | ✅ REV HD Hex 在表内 |
| **比赛时长 30s+8s+2min** | ✅ |
| **蜂群 RP = 16** | ⚠️ **v5.5 = 13，差 3 拿不到** |
| **传粉 1/2 RP = 4/7 翻倒** | ⚠️ **v5.5 保守策略 2 翻倒拿不到** |
| **启动装载 4 POLLEN** | ✅ |

## 关键 takeaway

**v5.5 单台机器人只靠"获胜 RP"拿 RP**（蜂群 + 传粉都拿不到）。T0 申请文书**强调设计极简 + 教学价值**，**不夸大性能**。

V0.9 仍未明说 5 项（翻倒物理阈值、POLLEN 装入方式限制、NECTAR 重量 vs 球数、TELEOP 能否动已装入的球等），等 V2 出来再迭代。

要不要 commit 这个仓库？