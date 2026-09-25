# Pedro Pathing — FTC 路径跟随库笔记

> 9.23 补：Q3 RAG 答不上 Pedro Pathing → 整理 GitHub 官方文档 + Quickstart 笔记进 data/raw/，下次 RAG 能直接答。

## 概述

- **Pedro Pathing** 是一个**反应式向量路径跟随 (Reactive Vector Follower)** 库，专为 FTC 机器人开发
- **开发者**: FTC Team 10158 (Scott's Bots)，现由 **Baron (FTC 20077)** 和 **Aarsh** 维护
- **License**: BSD-3-Clause
- **官网**: pedropathing.com
- **主仓库**: github.com/Pedro-Pathing/PedroPathing
- **Quickstart**: github.com/Pedro-Pathing/Quickstart
- **文档**: github.com/Pedro-Pathing-Projects/docs (Documentation-Old, archive)

## 核心特性

### 1. Bézier 曲线生成（不是样条/折线）
- 路径用 **Bézier 曲线**生成，比传统的折线/样条**更平滑、更快**
- 减少 jerk（加加速度突变），对精度任务（瞄准/抓取）友好
- 控制点 (control points) 可调，自动 tuner 会帮忙找最优

### 2. Reactive 反应式
- **不是预设轨迹，而是实时响应环境变化**
- 检测到障碍或偏差时**动态调整**，而不是"先规划后执行"
- 对 2024+ INTO THE DEEP 这种环境复杂的赛季特别有用

### 3. vs Road Runner 对比

| 维度 | Pedro Pathing | Road Runner |
|------|---------------|-------------|
| 路径生成 | **Bézier 曲线**（平滑） | 样条 / 折线 |
| 反应能力 | **Reactive**（实时调整） | 预设轨迹优先 |
| 平滑度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 学习曲线 | ⭐⭐⭐ (文档好) | ⭐⭐⭐⭐ (社区大) |
| 维护状态 | 活跃 (2026 仍在更新) | 较慢 |
| 适用场景 | 复杂环境、需要精度 | 简单直线/弧线 |

**经验法则**: 复杂赛季（INTO THE DEEP / BIOBUZZ 这种环境动态多）→ Pedro Pathing；简单任务 → Road Runner 也够。

## FTC 关系

- **集成方式**: 加进 FTC SDK Android Studio 项目的 `TeamCode/src/main/java/...` 目录
- **当前支持的赛季**: INTO THE DEEP (2024-2025), DECODE (2025-2026), **BIOBUZZ (2026-2027)** 兼容（社区持续更新）
- **比赛中的作用**:
  - **AUTO 阶段 (30s)**: 主要应用场景——从起点到 scoring zone 的自动导航
  - **TELEOP 阶段**: 辅助自动对齐到固定位置（手动微调）
  - **END GAME**: 倒计时到固定位置（如 hanging zone）
- **依赖**: 纯 Java，无外部 native lib，FTC SDK 控制 hub 直跑

## Quick Start (5 步)

### Step 1: 添加依赖
在 `build.gradle.kts` 加：
```kotlin
repositories { maven { url = uri("https://maven.pedropathing.com") } }
dependencies {
    implementation("com.pedropathing:pedro:1.0.5")  // 最新看 release
}
```

### Step 2: 初始化 Follower
```java
Follower follower = new Follower(hardwareMap);
follower.setStartingPose(new Pose(0, 0, 0));  // 起点位姿
```

### Step 3: 定义路径
```java
PathChain chain = follower.pathBuilder()
    .addPath(new BezierLine(new Pose(0, 0), new Pose(24, 24)))
    .setLinearHeadingInterpolation(Math.toRadians(0), Math.toRadians(90))
    .build();
follower.followPath(chain);
```

### Step 4: OpMode 循环里更新
```java
@Override
public void loop() {
    follower.update();
    telemetry.addData("x", follower.getPose().getX());
    telemetry.addData("y", follower.getPose().getY());
    telemetry.addData("heading", follower.getPose().getHeading());
}
```

### Step 5: 调参
- **PID 增益**: 用自带的 **Automatic Tuner** (`PedroPathingTuner` OpMode)
- **Localization**: 默认 Three Wheel Odometry，可切 Pinpoint / Road Runner 兼容
- **Bézier 控制点**: tuner 自动算最优

## 调参 Tips

1. **先 odometry 对齐**: 推 1 米看是否回到原点 (误差 < 2cm)
2. **再 PID**: 用 tuner 自动跑，找 `translationalPID` + `headingPID`
3. **Bézier 控制点**: 慢动作 + 录视频，逐段调整
4. **Reactive 参数**: `pathEndTimeout` / `pathEndTValue` 决定何时切下一段
5. **测试场景**: 先直线 → 加弧 → 加急转 → 加停止精度

## 选型决策（学生笔记）

**24306 适用场景**:
- ✅ AUTO 期需要精确到 scoring zone（POLLEN 投球 / NECTAR 上料）
- ✅ END GAME 倒计时到固定位置
- ✅ Teleop 自动对齐节省操作员精力
- ⚠️ 9 paths → AUTO 2 paths 简化（学生目标：减复杂度提可靠性）

**跟 Road Runner 的迁移**:
- Road Runner 1.0+ 用 `Pose2d` + `Trajectory`，Pedro 用 `Pose` + `PathChain`
- API 不兼容，要重写——但 Pedro 文档好，迁移成本 ~2 天

## 关键资源

- **官网**: https://pedropathing.com/
- **GitHub**: https://github.com/Pedro-Pathing/PedroPathing
- **Quickstart**: https://github.com/Pedro-Pathing/Quickstart
- **Discord**: Official Pedro Pathing Discord Server (GitHub README 里有 invite)
- **文档 archive**: https://github.com/Pedro-Pathing-Projects/docs

## 版本历史（关键）

| 版本 | 日期 | 关键改动 |
|------|------|---------|
| 2.0.4 | 2025-11 | 多模块项目拆分 (core/ftc 分开) |
| 1.0.5 | 2025-01 | Constants 修复、Power Caching |
| 1.0.0 | 2024-12 | 首次 library 形式发布 |

> 当前 (2026.9) 推荐用 **2.0.4+**（多模块结构 + JDK 1.8 兼容性修复）。

## 我的 FTC AUTO 应用方案 (待写)

- 9 paths → AUTO 2 paths 简化方案
- 第一段：从起始墙到 collector（4s）
- 第二段：从 collector 到 scoring zone（3s）
- 翻 HIVE 时用 Pedro 的 reactive 模式应对

> 注: 详细代码待后续 commit 到 FTC 项目仓库