# 24306 BIOBUZZ — 初始设计思路

> 9.13 凌晨 brainstorm。3 种子机制："双 intake + 单发射 + 升降送 tip"。
> 10:55 决策 (v2)：A 方案 — transfer 改 servo，**8 motor 卡线 0 余量**。
> 17:55 决策 (v3)：**双 intake 砍光**。POLLEN 爪子直接抓地面；NECTAR intake 反转推。**5 motor + 3 余量**。
> 17:59 决策 (v3.5)：**flywheel 改双电机驱动**。POLLEN 路径 = 爪子抓球 → 升降举到喂球位 → 双电机 flywheel 远射。**8 motor + 2 servo，卡线 0 余量**。
> 20:35 决策 (v5, 当前)：**极简化设计**。**砍爪子/升降/滑轮组/NECTAR intake/intake 反推/TIP 释放 servo**。**6 motor + 0 servo，余 2 motor**。AUTO 30s 装 4 POLLEN 进 HIVE FLOWER CELL = **88 分**（FLOWER POLLEN 2 + TIP 翻倒 20）。
> 等 Game Manual 第 5 章 (Scoring Details) 出 V2 后再迭代。

## 设计骨架 (v5, 9.14 20:35)

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
                         重力做功 → HIVE pivot 翻倒 → TIP 触发 (+20 分)
                              ↓
                         球落底 CELL → HIVE 翻倒完成
```

### 三大子系统 (v5 极简)

1. **双电机 flywheel** (POLLEN 远射机构, v5 唯一执行器)
   - 2× DC motor (M0, M4) **共驱 1 个飞轮** = 力矩翻倍, RPM 高, 远射精度高
   - 喂入：启动装载 4 POLLEN, 机器人倾斜角度让球靠重力自动滑入飞轮入口（无需 servo 释放）
   - 远射：双电机加速 1.5s 后射出 → HIVE FLOWER CELL → 球落入 HIVE 顶 CELL → 重力做功 → HIVE 翻倒
   - 1 球得分 = **FLOWER POLLEN 2 + TIP 翻倒 20 = 22 分**

2. **底盘 + 4 drive**
   - 4× DC motor (M6-M9, 必用)

3. **0 servo + 0 intake + 0 升降** (v5 砍了)
   - 不需要爪子（POLLEN 来源 = 启动装载, 不抓地面/不放 FLOWER）
   - 不需要升降（POLLEN 远射到 HIVE, 不需要举爪子到 HIVE 高）
   - 不需要 NECTAR intake（不做 TIP 反推, TIP 靠 POLLEN 落入 FLOWER 触发）
   - 不需要 TIP 释放 servo（HIVE 自动翻倒, 不需要机器人动作）

## 5 个关键问题 (v5 已解 #1)

1. ✅ **电机数** (6 motor, 2 余量) — 9.14 20:35 决策 v5
   - **6 motor 必用**: 4 drive (M6-M9) + 2 flywheel (M0, M4 双电机共驱 1 飞轮)
   - **0 servo**: 启动装载角度让 POLLEN 自动滑入飞轮（重力喂球）
   - **砍 2 motor**: 砍 POLLEN 升降 (motor + 滑轮组) + 砍 NECTAR intake (反推)
   - **2 motor 余量**: 备用 / 减重 / 联盟协同 (实战定)
   - **保留 REV Control Hub** (8 motor 限制, 远低于)

2. **球路由** (POLLEN 远射 vs 放置)
   - v5 远射 = 双电机 flywheel 力矩大 + 命中率靠瞄准 + V2 规则确认
   - V2 规则未出, 待 19606 老师聊

3. **TIP 翻倒机制** (v5 关键 insight) ✅ 部分确认
   - **靠 POLLEN 落入 HIVE 顶 CELL（FLOWER）的重力做功**触发 HIVE pivot 翻倒
   - HIVE 是双稳态: 一边 CELL 朝下 (有球) + 另一边 CELL 朝上 (空), 翻倒后状态交换
   - 1 球装入 FLOWER CELL = 触发 1 次 TIP = 20 分
   - 4 POLLEN 启动装载 = AUTO 30s 装 4 球 = 触发 4 次 TIP = 80 分 (加上 FLOWER POLLEN 2 × 4 = 8 分, 总 **88 分**)

4. **远射瞄准精度** (v5 核心难点)
   - 远射精度要求高 (HIVE FLOWER CELL 入口小, 球必须落入触发 TIP)
   - AprilTag 视觉伺服（V2 规则确认 HIVE 是否有 AprilTag）vs 预编程轨迹 vs 纯 PID
   - 9 月 kickoff meeting + 19606 老师聊

5. **联盟协同** (TELEOP 阶段 + 联盟伙伴)
   - 联盟 2 队/联盟, 4 队/场
   - partner 帮装 POLLEN 进其他 HIVE = 协同得分
   - 9 月 kickoff meeting 拍板

## 舵机 vs 电机 (v5 极简)

| 用途 | 用啥 | 数量 |
|------|------|------|
| 4 drive base | 4× DC motor | 4 |
| 2 flywheel (POLLEN 远射, 双电机共驱 1 飞轮) | 2× DC motor | 2 |
| ~~POLLEN 升降 (motor + 滑轮组)~~ | 砍 | 0 |
| ~~NECTAR intake~~ | 砍 | 0 |
| ~~POLLEN 爪子 (servo 张合)~~ | 砍 | 0 |
| ~~TIP 释放 (servo)~~ | 砍 | 0 |
| **DC motor 合计** | — | **6** ✅ (余 2 motor) |
| **servo 合计** | — | **0** ✅ |

## 决策 (9.14 20:35, v5 当前)

**v3.5 → v5 关键简化**:
- 砍 POLLEN 爪子 + 升降 + 滑轮组 → 启动装载 4 POLLEN 重力自动滑入飞轮
- 砍 NECTAR intake + 反推推球 → TIP 翻倒靠 POLLEN 落入 HIVE FLOWER 触发
- 砍 TIP 释放 servo → HIVE 自动翻倒

**理由**:
- 极简 = 6 motor + 0 servo, **机械最简**, 编程最简, 调试最快
- **TIP 翻倒靠球重力** (用户确认) = POLLEN 装入 FLOWER CELL 自动触发 = 高 ROI（22 分/球）
- AUTO 30s 装 4 POLLEN = **88 分**（之前估的 8 分少算了 80 分）
- 余 2 motor 给 partner 协同 / 减重 / 应急

**对比 v3.5**:
- v3.5: 8 motor + 2 servo 卡线, 爪子+升降+双电机 flywheel+intake, 复杂但丰富
- v5: 6 motor + 0 servo 余 2, 双电机 flywheel 极简, 得分更高（88 vs 估 28）

**候选**:
- A. **v5 极简** (当前画) — 4 drive + 2 flywheel + 0 servo = 6 motor, AUTO 88 分
- B. v3.5 双路径 — POLLEN 爪子 + NECTAR intake 反推 + 双 flywheel = 8 motor 卡线
- C. v3 爪子放置 — 5 motor + 3 motor 余量, 100% 命中但慢

## 9.14 待办 (周末)

- [ ] 跟 19606 老师 (ivymaker 同一人) 聊 30 分钟 — 确认 TIP 机制 + 双电机 flywheel 齿轮配置 + 飞轮材质/直径
- [ ] Game Manual V2 第 5 章 Scoring Details (9 月中出) — 确认 TIP 分值 + FLOWER POLLEN 分值
- [ ] AprilTag 视觉伺服方案 — V2 规则确认 HIVE 是否有 AprilTag
- [ ] Pedro Pathing 简化: 9 paths → AUTO 2-3 paths (装球循环) + TELEOP 一组
- [ ] 9 月 kickoff meeting 全员对 v5 投票
- [ ] v5 写进 .pptx / 文书 — 88 分 AUTO 极简 = T0 申请加分项