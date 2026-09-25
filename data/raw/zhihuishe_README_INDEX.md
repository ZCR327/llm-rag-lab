# 智能回收社 积分系统 — 项目文档索引

> 智能回收社积分管理系统（v5.9+）| Tkinter GUI + Flask HTTP API
> 最后更新：2026-06-19

## 新手入门

- [CONTRIBUTING.md](./CONTRIBUTING.md) — 开发流程、模块结构、调试技巧
- [CHANGELOG.md](./CHANGELOG.md) — 版本变更日志
- [项目详细调研报告.md](./项目详细调研报告.md) — 2026-06-19 全面代码审计（已归档到备份 zip）

## 核心文档

- [docs/HTTPS_SETUP.md](./docs/HTTPS_SETUP.md) — Nginx HTTPS 部署（TLS 1.2/1.3 + HTTP/2）
- [docs/api_reference.md](./docs/api_reference.md) — HTTP API 接口说明
- [docs/openapi.yaml](./docs/openapi.yaml) — OpenAPI 3.0 规范
- [docs/功能分布.md](./docs/功能分布.md) — 各模块功能分布概览

## 部署与运维

- [docker/nginx.conf](./docker/nginx.conf) — 反向代理配置（HTTPS 终结）
- [docker/ssl/](./docker/ssl/) — 自签名证书（localhost + 127.0.0.1，5 年）
- [.gitignore](./.gitignore) — 已忽略：备份、缓存、__pycache__、.db-journal、PNG 历史图表
- [requirements.txt](./requirements.txt) — Python 依赖清单

## 用户手册

- [功能优化列表.md](./功能优化列表.md) — 用户角度的功能改进清单
- [操作确认修复.md](./操作确认修复.md) — 关键操作的安全确认修复说明

## 项目结构（一览）

```
智能回收社积分系统/
├── main_v5.py                # 1.7KB 入口包装器
├── points_app/               # 核心业务包
│   ├── __init__.py           # 包入口 + 5 个启动钩子（迁移/缓存/shim/monkey-patch）
│   ├── legacy.py             # 12.7K 行 legacy 实现（兼容层）
│   ├── config.py             # 路径/常量/共享状态
│   ├── enums.py              # 9 个枚举
│   ├── migration.py          # JSON → SQLite 一次性迁移
│   ├── models/               # 9 个 dataclass
│   ├── security/             # RBAC + 审计 + 黑名单
│   ├── core/                 # 加密/会话/限流/缓存
│   ├── services/             # user/points/approval/notification
│   ├── data/                 # SQLite DAO
│   └── _plugins_loader_shim.py # 插件加载占位
├── data/                     # 数据目录（JSON + SQLite 双轨）
├── charts/                   # 图表输出目录
├── docker/                   # nginx + 自签名 SSL
├── docs/                     # 文档
├── backups/                  # 历史快照（zip 归档）
└── requirements.txt
```

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 GUI（首次自动迁移 JSON → SQLite）
python main_v5.py

# 默认管理员账号：admin / admin123
```

## 工具脚本

- [启动器.bat](./启动器.bat) — 一键启动（UTF-8 控制台）
- [远程登录.py](./远程登录.py) — 远程客户端登录工具

## 测试与验证

- [test_main_v5.py](./test_main_v5.py) — 主程序集成测试
- [test_features.py](./test_features.py) — 功能测试
- [test_v59.py](./test_v59.py) — v5.9 版本回归

> 测试脚本位于项目根目录，可直接运行：`python test_main_v5.py`
