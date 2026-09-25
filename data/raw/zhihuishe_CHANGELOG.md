# CHANGELOG — 智能回收社积分系统

> 所有重要变更记录于此。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

### 计划中
- 单元测试套件（至少覆盖 `points_app/data/` CRUD）
- 根目录散落子目录整合（`core/`, `models/`, `services/`, `modules/`, `ui/`, `utils/`, `plugins/`）
- legacy.py 废弃代码清理（删除已迁移到 modules 的部分）

---

## [5.9.1] — 2026-06-19

### 🎉 重大重构

#### Added（新增）

- **`points_app/` 包结构**：将 12.7K 行单体 `main_v5.py` 拆分为 8 个子包
  - `models/` — 9 个 dataclass（User / UserGroup / LoginLog / VerificationCode / PointsRecord / PointsTask / Notification / Feedback / ApprovalRequest）
  - `security/rbac.py` — Permission / RBACManager / AuditLogger / BlacklistManager / require_permission
  - `core/` — DataEncryption / SecureStorage / MiniProgramAuth / SessionManager / DataCache / RateLimiter / throttle
  - `services/` — user_service / points_service / approval_service / notification_service
  - `data/` — SQLite DAO（自动建表 + CRUD）

- **SQLite 持久化层**：
  - `points_app/migration.py` — JSON → SQLite 一次性迁移脚本（22.9KB）
  - `data/points.db` — 12 张表，34 条记录，约 200KB
  - 双轨制：legacy 继续读 JSON，新 DAO 读 SQLite（互不干扰）

- **HTTPS 部署支持**：
  - `docker/nginx.conf` — TLS 1.2/1.3 + HTTP/2 + HSTS + 80→301 重定向
  - `docker/ssl/` — 自签名证书（localhost + 127.0.0.1，5 年有效期）
  - `docs/HTTPS_SETUP.md` — 部署指南

- **5 个启动钩子**（`points_app/__init__.py`）：
  1. `_auto_migrate_if_needed()` — 自动检测 + 触发迁移
  2. `_invalidate_legacy_cache()` — 清陈旧缓存
  3. `_inject_plugins_loader_shim()` — 插件加载器占位
  4. `_patch_legacy_datacache()` — DataCache.get_users 扁平化修复
  5. `_patch_legacy_dv()` — 静默 DV 误报

#### Changed（变更）

- **`main_v5.py`**：从 520KB（12,725 行）瘦身到 1.7KB（包装器）
- **`legacy.py`**：原 `main_v5.py` 内容搬入 `points_app/legacy.py`（520KB，冻结状态）
- **`__getattr__` 兼容层**：保留所有 `from main_v5 import X` 调用，向下兼容

#### Fixed（修复）

- **`class PointsSystemApp` 缺父类**：原 `class PointsSystemApp:` 导致 `mainloop()` 递归爆栈
  - 修复：`class PointsSystemApp(tk.Tk):` + `tk.Tk.__init__(self)` + `self.root = self`
- **`from main_v5 import get_all_plugins` 循环依赖**：改为本地 `get_all_plugins()` 调用
- **重复 `__init__` 定义**：删除 line 6910 的副本
- **`DataCache.get_users` 嵌套 bug**：缓存返回 `{'users': {...}}`，新代码期望扁平 dict；monkey-patch 修复
- **`AuditLogger` Flask request 检测**：`if 'request' in dir()` 改为 try/except
- **`DataEncryption` 缺 cryptography**：检测到缺失时优雅降级（warn 不 raise）
- **`validate_username` 规则**：≥3 字符 + 支持中文（`[a-zA-Z0-9_\u4e00-\u9fff]+`）
- **`paginate_list` 返回顺序**：legacy 返回 `(items, total_pages, total)`，service 内部 normalize
- **`plugins_loader` 模块缺失**：`sys.modules` 注入占位模块（不再恢复废弃文件）
- **`marks.json` 数据污染**：清理 4 个用户账户（admin/zcr/唐荣泽/赵昶瑞），删除 `admin` 默认凭证
- **`remote_client_config.json` 默认凭证泄露**：删除明文 token

#### Removed（移除）

- 10 个冗余文件：`main_hdmi.py`、`main_v5_extensions.py`、`main_v5_fixed.py`、`find_*.py`、`move_sys_tab.py`、`feature_enhancements.py`、`final_integration.py`
- 2 个 `启动器.bat`（保留 UTF-8 版本）
- 227 张历史 PNG 图表（移入回收站）
- 空 `src/` 目录

---

## [5.9.0] — 2026-06-11

### Added

- 初始 Git 仓库（baseline commit `ab62c51`）
- 73 个源文件
- Tkinter GUI + Flask HTTP API
- 完整的用户/积分/审批/通知/反馈功能

---

## [5.5] — 2026-05-23

### Added

- 主版本切换（`main_v6` 系列备份）

---

## 历史快照

所有历史 `main_v5` 版本备份见 `backups/` 目录：
- `main_v5_20260505_v1.py` ~ `main_v5_20260619_v2.py`（28 个版本）
- `backup_20260520_194601.zip`（早期 zip 备份）
- `audit-20260619.zip`（本次重构清理前的快照，含 JSON 数据 + 原始 main_v5 + 清理清单）

---

## 变更类型图例

- 🎉 重大重构
- ✅ 新增功能
- 🔧 变更（兼容）
- 🐛 修复
- 🗑️ 移除
- 📝 文档
- ⚡ 性能
- 🔒 安全
