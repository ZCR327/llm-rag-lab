# Pedro Pathing — Bézier + Pure Pursuit 算法数学详解

> 补充 pedro_pathing.md 的算法原理部分 (RAG 答 "Pedro Pathing 算法" 用)

## 1. 三次 Bézier 曲线 (Cubic Bézier)

3 次 Bézier 由 4 个控制点 P0/P1/P2/P3 定义, 公式:

```
B(t) = (1-t)³·P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³·P3
其中 t ∈ [0, 1]
```

**几何意义**:
- P0: 起点 (机器人当前位置)
- P1, P2: 控制点 (决定曲线"弯曲方向", 不在曲线上)
- P3: 终点 (目标位置)

**导数 (切向量)**:
```
B'(t) = 3(1-t)²·(P1-P0) + 6(1-t)t·(P2-P1) + 3t²·(P3-P2)
```

切向量决定机器人朝向 (heading = atan2(B'(t).y, B'(t).x))

**优势 vs 折线/样条**:
- C² 连续 (曲率连续), 机器人运动平滑
- 起点终点切向量由 P1/P3 决定 (灵活调速)
- 局部控制: 改 P1 只影响曲线前半段

**Pedro Pathing 用 BezierLine** (起点+终点+隐式控制点) 或 BezierCurve (4 个控制点)

## 2. Pure Pursuit 路径跟随

**核心思想**: 在路径前方 lookahead_inches 距离处找"目标点", 用这个点控制转向

**算法**:
```
1. 给定当前位置 robot (x, y, heading)
2. 找曲线上距离 robot 最近的点 t0 (用 project_point)
3. 从 t0 开始, 沿曲线累积弧长, 找到累计 = L 的点 → target
4. α = atan2(target.y - robot.y, target.x - robot.x) - heading
   (目标相对机器人朝向的偏角)
5. 曲率 κ = 2·sin(α) / L
6. 角速度 ω = v · κ
   (速度越快, lookahead 越长 → 路径越平滑)
7. 线速度 v: 大曲率降速, 直线加速, 终段 (t > 0.85) 线性减速到 0
```

**Reactive (Pedro Pathing vs Road Runner 关键区别)**:
- 速度 v 变化时, 动态调整 lookahead: L = base_L + k · v
- v 高 → lookahead 长 → 减少高频抖动
- v 低 → lookahead 短 → 急弯不脱轨

## 3. 仿真结果 (本仓库实测)

在 `output/path_demo.png` S 曲线跟踪 (P0=(0,0), P1=(30,0), P2=(60,60), P3=(90,60)):
- 路径总长: 110.7 inch
- 6 秒后到 (98, 62.8), heading 116.4°
- 距 P3 = 8.5 inch
- 终段减速逻辑触发 (t > 0.95 v → 0)

**偏差 8.5 inch 原因**: 终段 (t > 0.85) min_v=8 inch/s 仍有惯性, 简单 Pure Pursuit 无最终 heading 收敛
**改进**: 加 heading interpolation (setLinearHeadingInterpolation) + 更细减速

## 4. Pedro Pathing 实际实现要点

**Path Builder 模式**:
```java
PathChain chain = follower.pathBuilder()
    .addPath(new BezierLine(p0, p3))
    .setLinearHeadingInterpolation(h0, h1)
    .addPath(new BezierLine(p3, p6))
    .setLinearHeadingInterpolation(h1, h2)
    .build();
follower.followPath(chain);
```

**PID 三件套** (用 PedroPathingTuner 跑):
- translational PID: x/y 跟踪
- heading PID: 朝向收敛
- drive PID: 直线响应

**Localization 选型**:
- Pinpoint (REV-11-1299) - 推荐, 高精度
- Three Wheel Odometry - 老方案, 误差大
- IMU + 视觉 - 实验性

## 5. vs Road Runner 对比

| 维度 | Pedro Pathing | Road Runner |
|------|---------------|-------------|
| 路径生成 | **Bézier 曲线** | 样条/折线 |
| 跟随 | **Reactive Vector Follower** | Pure Pursuit 静态 L |
| 平滑度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 社区 | 2024+ 新, 文档好 | 5 年+, 教程多 |
| 维护 | 活跃 (Baron 持续) | 较慢 |
| 推荐场景 | 复杂赛季, 高精度 | 简单任务 |

## 6. 调参步骤 (真机)

1. 推 1 米看 translationalPID
2. 转 90° 看 headingPID
3. 走直线看 drivePID
4. 急弯看 centripetalScaling
5. Automatic Tuner (PedroPathingTuner OpMode) 全自动算

## 7. 本仓库代码映射

- `bezier_curve.py` — Bézier 数学库 (point/tangent/sample/length/project/lookahead)
- `path_follower.py` — Pure Pursuit + Reactive follower 仿真
- `visualizer.py` — matplotlib 输出 PNG
- `auto_path_planner.py` — 9→2 paths 优化器
- `android/TeamCode/` — Android Studio 集成 (Java)