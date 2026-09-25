# CONTRIBUTING — 智能回收社积分系统

> 开发指南 | 适用于 v5.9+ 模块化版本
> 最后更新：2026-06-19

## 开发环境

- **Python**：3.12（推荐；3.10/3.11 也兼容，GUI 在 3.12 验证）
- **依赖**：`pip install -r requirements.txt`
- **IDE**：PyCharm / VSCode 均可
- **操作系统**：Windows 10/11（GUI 主用），Linux 兼容（API + CLI）

## 项目结构

```
points_app/                   # 核心业务包
├── __init__.py              # 包入口（启动钩子）
├── legacy.py                # 12.7K 行 legacy 实现（兼容层，未重构）
├── config.py                # 路径/常量
├── enums.py                 # 9 个枚举
├── migration.py             # JSON → SQLite 迁移
├── models/                  # 9 个 dataclass
│   ├── user.py              # User / UserGroup
│   ├── points.py            # PointsRecord / PointsTask
│   ├── notification.py      # Notification
│   ├── feedback.py          # Feedback
│   └── approval.py          # ApprovalRequest
├── security/                # 安全层
│   ├── rbac.py              # Permission / RBACManager / AuditLogger / BlacklistManager
│   └── __init__.py          # require_permission 装饰器
├── core/                    # 基础设施
│   ├── __init__.py          # DataEncryption / SecureStorage / SessionManager /
│   │                        # DataCache / RateLimiter / throttle
│   └── (其他按需扩展)
├── services/                # 业务服务
│   ├── user_service.py      # 用户 CRUD / 排名 / 统计
│   ├── points_service.py    # 积分增减 / 排行榜
│   ├── approval_service.py  # 审批流
│   └── notification_service.py # 通知推送
└── data/                    # 数据层
    └── __init__.py          # SQLite DAO（自动建表 + CRUD）

main_v5.py                    # 1.7KB 入口（包装器）
```

## 启动流程（5 个启动钩子）

`points_app/__init__.py` 在包导入时按顺序执行以下钩子：

1. **`_auto_migrate_if_needed()`** — 检查 `data/points.db` 是否存在，不存在则从 JSON 迁移（首次启动自动触发）
2. **`_invalidate_legacy_cache()`** — 调用 `DataCache.invalidate()` 清掉 legacy 的陈旧缓存（30s TTL）
3. **`_inject_plugins_loader_shim()`** — 注入 `sys.modules['plugins_loader']` 占位模块（替代已废弃的插件加载器）
4. **`_patch_legacy_datacache()`** — monkey-patch `DataCache.get_users`，返回扁平用户字典（legacy 缓存返回 `{'users': {...}}` 嵌套结构）
5. **`_patch_legacy_dv()`** — 静默 DV 库的误报警告

**重要**：钩子顺序不能乱。修改前请阅读 `points_app/__init__.py` 顶部注释。

## 开发规范

### 1. 新增功能

- **首选**：在 `points_app/services/` 添加新 service 类
- **避免**：在 `points_app/legacy.py` 里新增代码（已冻结，仅做兼容）
- **数据模型**：在 `points_app/models/` 添加 dataclass，并在 `__init__.py` 导出
- **数据库变更**：修改 `data/__init__.py` 的建表 SQL + 同步到 `migration.py`

### 2. 修改 legacy 代码

- legacy 是 frozen state，所有 `self.xxx` 引用（约 5,000+ 处）依赖 `__init__` 中初始化的属性
- 新增 GUI 组件属性必须在 `__init__` 头部（`tk.Tk.__init__(self)` 之后）赋初值，否则会触发 `AttributeError`
- 不要修改 `class PointsSystemApp(tk.Tk):` 的父类继承，否则 MRO 变动会破坏大量 `super().__init__()` 调用

### 3. 命名约定

- **类名**：`PascalCase`（如 `RBACManager`、`AuditLogger`）
- **函数/方法**：`snake_case`（如 `get_user_by_id`、`invalidate_cache`）
- **常量**：`UPPER_SNAKE_CASE`（如 `WINDOW_TITLE`、`MAX_LOGIN_ATTEMPTS`）
- **私有**：`__` 前缀（双下划线触发 name mangling）

### 4. 错误处理

- **GUI 错误**：用 `tkinter.messagebox.showerror()`，不要 raise 到主循环
- **API 错误**：返回 `{'success': False, 'error': '...', 'code': 'XXX'}` 格式
- **日志**：`logging.getLogger(__name__)`，禁止 `print()`

## 调试技巧

### GUI 启动失败

```python
# 在 main_v5.py 入口加 print
import traceback
try:
    app.mainloop()
except Exception:
    traceback.print_exc()
```

常见错误：
- `RecursionError: ... self.tk` → `tk.Tk.__init__(self)` 没在 `__init__` 头部调用
- `AttributeError: 'PointsSystemApp' object has no attribute 'X'` → 在 `__init__` 头部加 `self.X = None`
- `TclError: application has been destroyed` → 测试环境无显示（headless），真机没问题

### 数据迁移失败

```bash
# 手动重新迁移（先备份！）
python -c "from points_app.migration import migrate_json_to_sqlite; migrate_json_to_sqlite(force=True)"
```

### 缓存污染

```python
# 清掉所有缓存
from points_app.core import DataCache
DataCache.invalidate()
```

## 测试

```bash
# 集成测试（启动 GUI + API）
python test_main_v5.py

# 功能测试
python test_features.py

# 版本回归
python test_v59.py
```

测试脚本位于项目根目录。

## 提交规范

- **提交频率**：每个独立功能点提交一次
- **Commit 格式**：`<type>(<scope>): <subject>`
  - `feat(points): 添加积分转账功能`
  - `fix(gui): 修复登录窗口闪退`
  - `docs: 更新 README_INDEX`
  - `refactor: 拆分 PointsSystemApp`
- **提交前**：本地跑过 `test_main_v5.py` 再提交

## 发布流程

1. 更新 `CHANGELOG.md`（标注日期 + 变更类型）
2. 更新 `README_INDEX.md`（如有新文档）
3. 测试：本地完整跑通 GUI + API
4. 备份 `data/marks.json` + `data/points.db` 到 `backups/`
5. Git tag：`v5.10` 格式
6. 推送到远程

## 联系

- 项目负责人：智能回收社开发组
- 问题反馈：通过项目 issue 或 `feedback.json` 中的渠道
