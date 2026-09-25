# 24306 BIOBUZZ — Android PedroPathing TeamCode

> Java OpMode + Gradle 配置, 复刻 PedroPathing 官方 Quickstart 模式
> 配合 `../output/auto_paths.json` (Python 端规划) 使用

## 5 步上手

```powershell
# 1. 准备 FtcRobotController 完整项目 (一次性)
git clone https://github.com/FIRST-Tech-Challenge/FtcRobotController.git
cd FtcRobotController

# 2. 把这个目录的 TeamCode 拷过去
xcopy /E /I <pedro_pathing>\android\TeamCode TeamCode

# 3. 同步 Python 生成的路径 JSON
cd <pedro_pathing>
python auto_path_planner.py
.\android\sync_paths.ps1

# 4. Android Studio: File > Open > FtcRobotController > Gradle Sync
# 5. Build > Make Project > 部署到 Control Hub
```

详细步骤: [docs/ANDROID_INTEGRATION.md](docs/ANDROID_INTEGRATION.md)

## 文件清单

| 文件 | 作用 |
|---|---|
| `PedroAutoOpMode.java` | AUTO OpMode 主体 |
| `PoseJsonParser.java` | 读 Python 端 JSON |
| `constants/FConstants.java` | Follower 配置 (drive motor + PID) |
| `constants/LConstants.java` | Localizer 配置 (Pinpoint odometry) |
| `build.gradle` | Gradle 依赖 (PedroPathing 2.0.4 + FTC SDK 10.3) |
| `sync_paths.ps1` | 复制 `auto_paths.json` 到 assets/ |
| `docs/ANDROID_INTEGRATION.md` | 完整集成步骤 |

## 当前版本

- **PedroPathing**: 2.0.4 (maven.pedropathing.com)
- **FTC SDK**: 10.3 (FtcRobotController v10.3)
- **JDK**: 17+ (Java 21 兼容)
- **AGP**: 8.x (Android Studio Hedgehog+)
- **状态**: placeholder PID, 真机跑 Automatic Tuner 后覆盖

## 已知问题 / TODO

1. **heading 硬编码** — `PedroAutoOpMode.java` 用了 hardcoded `[0, π/4, 0]`, 应该从 JSON 读
2. **Flywheel 没接** — 双电机飞轮需要额外 subsystem
3. **PID 待 tune** — `FConstants.java` 是 placeholder, 真机跑后替换
4. **国内网络** — maven.pedropathing.com 偶尔不稳, 考虑镜像或本地 aar