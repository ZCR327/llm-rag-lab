# 24306 BIOBUZZ — 初始设计思路

> 9.13 凌晨 brainstorm。3 种子机制："双 intake + 单发射 + 升降送 tip"。
> 10:55 决策：A 方案 — transfer 改 servo 摆动拨片，elevator 保留 motor，**8 motor 卡线，0 余量**（不升级 REV v2）。
> 等 Game Manual 第 5 章 (Scoring Details) 出 V2 后再迭代。

## 设计骨架

```
       ┌─ 升降 (elevator, motor + 丝杠)  ─ 把球举到 HIVE 顶部 CELL 上方
       │
左 intake  ←→  中央储存 + 球路分配  ←→  右 intake
                       │
                  单 launcher (flywheel, motor)
                       ↓
                  射到 HIVE 触发 TIP
```

### 三大子系统

1. **双 intake** (双进料口)
   - 左 intake: 7.1cm 黄球 (POLLEN)
   - 右 intake: 9.1cm 球 (NECTAR)
   - **球路由**: 颜色识别 (黄 vs ?) + 大小筛选滚筒
   - ✅ 8 电机限制 solved (transfer 改 servo 摆动拨片, 见下)

2. **单 launcher** (飞轮发射)
   - 1× DC motor + 飞轮
   - 发射到 HIVE 哪个 CELL? 顶部 (装球) 还是底部 (冲顶)?
   - 等待 V2 规则

3. **升降送 tip** (elevator + 触发)
   - 1× DC motor + 丝杠
   - 举球到 HIVE 顶部 CELL 上方
   - 球落下触发 TIP 翻倒
   - 升降行程 ≥ 30-40cm (HIVE 估计高度)

## 5 个关键问题 (明天细看 + 19606 老师聊)

1. ✅ **电机数** (8 motor 卡线, 0 余量) — 9.13 10:55 决策
   - 保留 8 motor: 4 drive + 2 intake (左/右) + 1 flywheel + 1 elevator
   - transfer 改 1× servo 摆动拨片 (60° 摆动把球推进 flywheel, 不占 motor)
   - tip 释放改 1× servo (挡块释放, 不占 motor)
   - **不升级 REV v2**, 保持原 REV Control Hub (8 motor 限制即可)

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
| 2 intake | 2× DC motor | 2 |
| 1 flywheel | 1× DC motor | 1 |
| 1 elevator | 1× DC motor (丝杠) | 1 |
| 1 ball transfer | ~~1× DC motor (传送带)~~ → **1× servo 摆动拨片** | 0 |
| tip 释放 | 1× servo (挡块释放) | 0 |
| 球路切换 | 1× servo (clutch, 备用) | 0 |
| **DC motor 合计** | — | **8** ✅ |

### 决策 (9.13 10:55)

**选 A (修订)**: transfer 改 servo 摆动拨片，tip 释放改 servo，**保留 8 motor**（不升级 REV v2）。

理由：servo 摆动拨片 + 挡块释放是 FTC 老套路，力矩 / 速度 / 精度都够；elevator 必须 motor + 丝杠（举 0.5kg × 30cm 行程，servo 6 kg·cm 力矩临界）。**机械稳 + 编程可控**比"省 1 motor 升级 REV v2"重要。

其他选项存档：
- ~~B. 砍 1 motor: intake 双侧共用 1 motor + servo clutch 切换~~ (复杂, 球路冲突风险)
- ~~C. 砍 1 motor: 不做 ball transfer, 升降里直接进~~ (球流卡顿, 不取)

## 9.13 待办 (周末)

- [ ] 细看 Game Manual V1 第 3 章 Game Overview
- [ ] 跟 ivymaker 老师 (19606 同一人) 聊 30 分钟 — 实战经验
- [ ] 等 Game Manual V2 (Scoring Details 章节, 估计 9 月中出)
- [ ] 9 月 kickoff meeting 全员对思路
- [ ] 看 HIVE 实物长什么样 (FIRST HQ 一般 kickoff 时给图)
