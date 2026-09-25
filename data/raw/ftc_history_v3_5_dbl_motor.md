# 24306 BIOBUZZ — 初始设计思路

> 9.13 凌晨 brainstorm。3 种子机制："双 intake + 单发射 + 升降送 tip"。
> 10:55 决策 (v2)：A 方案 — transfer 改 servo，**8 motor 卡线 0 余量**。
> 17:55 决策 (v3)：**双 intake 砍光**。POLLEN 爪子直接抓地面；NECTAR intake 反转推。**5 motor + 3 余量**。
> 17:59 决策 (v3.5, 当前)：**flywheel 改双电机驱动**。POLLEN 路径 = 爪子抓球 → 升降举到喂球位 → 双电机 flywheel 远射到 HIVE FLOWER CELL。**8 motor + 2 servo，卡线 0 余量**。
> 等 Game Manual 第 5 章 (Scoring Details) 出 V2 后再迭代。

## 设计骨架 (v3.5, 9.13 17:59)

```
       ┌─ 升降 (motor + 滑轮组 pulley)  ─ 举爪子到 flywheel 喂球位 (≤30cm)
       │
右 POLLEN 爪子 (1 servo 张合) → 抓地 → 喂入双电机 flywheel → 远射 HIVE FLOWER CELL → 2 分/球
              ↑                              ↑
       爪子入口贴地张开              2 motor (M0, M4) 共驱 1 飞轮
                                                              (力矩大, 远射精度高)

左 NECTAR intake (1 motor 滚筒, 吸+反转推) → 推入 HIVE 底 CELL → 触发 TIP → 20 分
              ↑
       intake 反转 = 推球 + 机器人前进配合, 不靠 flywheel 远射
```

### 四大子系统 (v3.5 修订)

1. **POLLEN 爪子** (抓球工具)
   - 1× servo 张合 (S0)
   - **直接抓地面球** (爪子入口贴地张开, 球滚入, 张合夹紧)
   - 抓球后升到 flywheel 喂球位 → 张开喂入飞轮
   - 砍 1 motor (原 POLLEN intake 滚筒, 改爪子直接抓)

2. **双电机 flywheel** (POLLEN 远射机构, 替代 v3 的"爪子精准放置")
   - 2× DC motor (M0, M4) **共驱 1 个飞轮** = 力矩翻倍, RPM 高, 远射精度高
   - 喂入 → 高速旋转 → 远射到 HIVE FLOWER CELL (2 分/球, 靠力矩 + 瞄准)
   - 双电机 1 飞轮的 FTC 实战老套路, 比单电机飞轮远 30-50%
   - 比 v3 爪子放置: 远射可多球快速发射, 命中看瞄准; v3 放置: 100% 命中但慢

3. **NECTAR intake** (吸+反转推, 替代 flywheel 远射)
   - 1× DC motor (M3) + 滚筒 (吸+反转推, 一体)
   - 吸球 → 机器人贴 HIVE 围栏 → intake 反转推球入 HIVE 底 CELL → 触发 TIP (20 分)
   - 砍 flywheel (NECTAR 重 9.1cm, 远射精度差, intake 推更稳)

4. **升降滑轮组** (服务 POLLEN 爪子)
   - 1× DC motor (M5) + 滑轮组 (pulley system)
   - 举爪子到 flywheel 喂球位 (≤30cm, 不用举到 HIVE 高)
   - 滑轮组: 主动滑轮 + 动滑轮 (省力, 力矩减半) + 钢丝绳 + 张紧器
   - 比丝杠: 轻 / 便宜 / 行程灵活

5. **底盘 + 4 drive**
   - 4× DC motor (M6-M9, 必用)

## 5 个关键问题 (明天细看 + 19606 老师聊)

1. ✅ **电机数** (8 motor 卡线, 0 余量) — 9.13 17:59 决策 v3.5
   - **8 motor 必用**: 4 drive (M6-M9) + 1 NECTAR intake (M3) + 1 POLLEN 升降 (M5) + **2 flywheel (M0, M4) 双电机共驱**
   - **砍 2 motor**: 砍 POLLEN intake 滚筒 (旧) + 砍 transfer (旧)
   - **0 motor 余量**: 卡线, 升级 REV v2 才能再加
   - **保留 REV Control Hub** (8 motor 限制刚好用满)
   - servo 数: 1 (POLLEN 爪子张合 S0) + 1 (tip 释放挡块 S1, 备用) = 2 servo

2. **球路由** (POLLEN vs NECTAR)
   - 颜色识别 (黄 vs 颜色待定)
   - 大小筛选滚筒 (7.1cm 过小孔, 9.1cm 过大孔)
   - 触觉/光电开关

3. **升降行程** (30-40cm)
   - 电机 + 丝杠: 慢但稳
   - 气动: 快但法规可能限
   - 橡皮筋储能 + 释放: 简单但控制精度低

4. **TIP 触发力学** (核心未验证)
   - 球落下能不能翻 HIVE?
   - 需要多重的球?
   - HIVE 的 pivot 阻尼多大?
   - **必须看 Game Manual V2 第 5 章 Scoring Details**

5. **Launcher 装哪** (发射目标)
   - 顶部 CELL (装球) - 较远
   - 底部 CELL (冲顶) - 较近
   - 两侧 - 触发 TIP
   - 等 V2 规则

## 舵机 vs 电机 (FTC R9 规则)

| 用途 | 用啥 | 数量 |
|------|------|------|
| 4 drive base | 4× DC motor | 4 |
| 1 NECTAR intake (吸+反转推) | 1× DC motor | 1 |
| 1 POLLEN 升降 (motor + 滑轮组) | 1× DC motor | 1 |
| **2 flywheel (POLLEN 双电机共驱 1 飞轮)** | **2× DC motor** | **2** |
| ~~1 POLLEN intake 滚筒 (旧)~~ | 砍 (改爪子直接抓地面) | 0 |
| ~~1 elevator (旧)~~ | 砍 (NECTAR 不举升) | 0 |
| ~~1 transfer (旧)~~ | 砍 (球路由没了) | 0 |
| POLLEN 爪子张合 | 1× servo | 0 |
| tip 释放挡块 (备用) | 1× servo | 0 |
| 球路切换 clutch (备用) | 1× servo | 0 |
| **DC motor 合计** | — | **8** ✅ (卡线 0 余量) |

### 决策 (9.13 17:59, v3.5 当前)

**v3 → v3.5 关键变化**: flywheel 改**双电机共驱**（不是 v3 砍掉的单 flywheel，也不是 v2 旧方案），POLLEN 路径 = 爪子抓球 → 升降举到喂球位 → 双电机 flywheel 远射到 HIVE FLOWER CELL。

理由：双电机 flywheel 力矩大 + RPM 高 + 远射精度高（比单 flywheel 远 30-50%），POLLEN 7.1cm 球小，远射反而命中率高；爪子抓球省 intake 滚筒的 1 motor；升降滑轮组举爪子到喂球位（不举到 HIVE 高，更省力）。**8 motor 卡线 0 余量**，比 v3 5 motor 多 3 motor 用在 flywheel 提升战斗力。

v3.5 候选方案对比（待你定）：
- **A (当前)**: 保留爪子 + 升降 + 双电机 flywheel → 8 motor + 2 servo
- B: 砍爪子 + 升降，POLLEN intake 滚筒 + 双电机 flywheel 远射 → 8 motor + 0 servo (更简)
- C: 保留 v3 爪子放置（2 分/球 100% 命中）不靠 flywheel → 5 motor + 3 motor 余量

历史存档：
- ~~v2 方案 (8 motor, flywheel + 双 intake + transfer)~~ 复杂
- ~~v3 方案 (5 motor 爪子直接放置)~~ 改 v3.5 双电机 flywheel 远射

## 9.13 待办 (周末)

- [ ] 细看 Game Manual V1 第 3 章 Game Overview
- [ ] 跟 ivymaker 老师 (19606 同一人) 聊 30 分钟 — 实战经验
- [ ] 等 Game Manual V2 (Scoring Details 章节, 估计 9 月中出)
- [ ] 9 月 kickoff meeting 全员对思路
- [ ] 看 HIVE 实物长什么样 (FIRST HQ 一般 kickoff 时给图)
