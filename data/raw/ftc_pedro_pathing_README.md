# 24306 BIOBUZZ Pedro Pathing 工具箱

> Python 实现 + 仿真 + Android Pose JSON 输出 (v5.5 极简策略, 9→2 paths)
> 不依赖 Android Studio / FTC SDK, 纯 Python 学习用

## 文件结构

```
pedro_pathing/
├── bezier_curve.py          # Bézier 数学: point/tangent/sample/length/project/lookahead
├── path_follower.py          # Pure Pursuit + Reactive follower (RobotState 模拟)
├── visualizer.py             # matplotlib 输出 PNG (path_demo + field_demo)
├── auto_path_planner.py      # 9→2 优化 + Pose JSON + Markdown 报告
├── README.md                 # 本文件
└── output/
    ├── path_demo.png         # S 曲线 + 机器人跟踪轨迹
    ├── field_demo.png        # FTC 半场 9→2 对比图
    ├── auto_paths.json       # Pedro Pathing 兼容 Pose JSON (Android 端读)
    └── auto_paths_pretty.md  # 给人看的表格报告
```

## 5 分钟跑一遍

```powershell
# 安装依赖
pip install -U matplotlib numpy python-dotenv

# 仿真 + 可视化 (生成 path_demo.png + field_demo.png)
cd D:\Users\xiaomi\Desktop\FTC\24306\2026-2027_BIOBUZZ\pedro_pathing
python visualizer.py

# 路径规划器 + Pose JSON 输出
python auto_path_planner.py
python auto_path_planner.py --time      # 看用时
python auto_path_planner.py --optimize  # 9 paths → 2 paths 最优组合枚举
```

## 核心算法

### Bézier 曲线 (bezier_curve.py)
- 3 次 Bézier: `B(t) = (1-t)³·P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³·P3`
- API: `.point(t)` `.tangent(t)` `.sample(n)` `.length()` `.project(p)` `.lookahead_point(p, L)`
- 实测 S 曲线 length=110.69 inch, lookahead 算法正确

### Pure Pursuit 跟随 (path_follower.py)
- 算法: `κ = 2·sin(α) / L`, `ω = v·κ`
- Reactive: 速度越快 lookahead 越长 (避免高频抖动)
- 自适应速度: 大曲率降速, 终段 (t > 0.85) 允许减速到 0
- 实测 S 曲线跟踪: 6 秒后到 (98, 62.8), 距 (90, 60) 8.5 inch (算法工作, 终点欠调)

### 路径规划 (auto_path_planner.py)
- v5.5 决策: 9 paths → 2 paths (AUTO 简化)
- AUTO-1: 起始墙 → collector (17 inch / 0.34s @ 50ips)
- AUTO-2: collector → scoring zone (72 inch / 1.45s @ 50ips)
- 总 89.3 inch / 1.79s (vs 9 paths 544.5 inch / 10.89s, **节省 84%**)
- AUTO 30s 余量 28.21s (留时间装球/瞄准/远射)

## Android 端用法 (Pedro Pathing 0.1.x 兼容)

```java
// 读 auto_paths.json (可用 Gson/Moshi)
PathChain chain = follower.pathBuilder()
    .addPath(new BezierLine(
        new Pose(12.0, 12.0),
        new Pose(24.0, 24.0)
    ))
    .setLinearHeadingInterpolation(0.0, Math.PI / 4)
    .addPath(new BezierLine(
        new Pose(24.0, 24.0),
        new Pose(72.0, 78.0)
    ))
    .setLinearHeadingInterpolation(Math.PI / 4, 0.0)
    .build();
follower.followPath(chain);
```

## v5.5 关键决策 (回顾)

- 6 motor (4 drive + 2 flywheel 共驱 1 飞轮) + 0 servo
- AUTO 30s 装 4 POLLEN → 触发 HIVE TIP = 28 分
- 极限 82 分 (翻 2 次 + 16 POLLEN + PARK + AUTO 停靠)

## 待做 (TODO)

1. Android Studio 集成 Pedro Pathing 库 (gradle + SDK 真机调试)
2. 远射瞄准精度: AprilTag 视觉伺服 (Game Manual V2 待确认 HIVE 是否有 AprilTag)
3. NECTAR intake 模块 (v6)
4. Heading 收敛调参 (当前 Pure Pursuit 终点偏差 8.5 inch)
5. 仿真 → Real Robot 控制闭环 (Python ↔ Control Hub over WiFi)