# 积分系统功能分类文档
> 生成时间: 2026-05-06
> 版本: v5.7

---

## 一、用户管理 (34个)

### 登录注册
| 功能 | 说明 |
|------|------|
| `do_login` | 用户登录 |
| `logout` | 用户登出 |
| `show_login_frame` | 显示登录界面 |
| `show_register_dialog` | 显示注册对话框 |

### 用户操作（管理员）
| 功能 | 说明 |
|------|------|
| `admin_add_user` | 添加用户 |
| `admin_delete_user` | 删除用户 |
| `admin_batch_delete` | 批量删除用户 |
| `admin_toggle_user` | 启用/禁用用户 |
| `admin_reset_password` | 重置密码 |
| `admin_reset_points` | 重置积分 |
| `admin_restore` | 恢复数据 |
| `show_all_users` | 显示所有用户 |
| `change_user_role_dialog` | 修改用户角色 |

### 用户权限操作
| 功能 | 说明 |
|------|------|
| `assign_user_to_group` | 分配用户到分组 |
| `user_transfer` | 用户积分转账 |
| `show_user_distribution` | 显示用户分布 |

### 用户个人中心
| 功能 | 说明 |
|------|------|
| `show_user_frame` | 显示用户界面 |
| `user_add_points` | 用户充值积分 |
| `user_reduce_points` | 用户消费积分 |
| `user_check_points` | 查看积分 |
| `user_show_mall` | 积分商城 |
| `user_show_rankings` | 查看排行榜 |
| `user_my_exchanges` | 我的兑换 |
| `user_submit_feedback` | 提交反馈 |
| `user_view_my_feedback` | 查看我的反馈 |
| `user_view_notifications` | 查看通知 |
| `show_change_password_dialog` | 修改密码对话框 |

### 管理功能
| 功能 | 说明 |
|------|------|
| `admin_backup` | 数据备份 |
| `admin_delete_backup` | 删除备份 |
| `admin_export` | 数据导出 |
| `admin_import` | 数据导入 |
| `show_admin_frame` | 显示管理界面 |

---

## 二、积分管理 (7个)

| 功能 | 说明 |
|------|------|
| `admin_modify_points` | 修改积分 |
| `show_points_trend` | 积分趋势图 |
| `show_points_history` | 积分历史 |
| `show_my_points_detail` | 我的积分明细 |
| `add_product_dialog` | 添加商品 |
| `edit_product_dialog` | 编辑商品 |
| `delete_product_dialog` | 删除商品 |

---

## 三、数据操作 (8个)

| 功能 | 说明 |
|------|------|
| `backup_data` | 备份数据 |
| `auto_backup` | 自动备份 |
| `restore_data` | 恢复数据 |
| `export_dashboard_report` | 导出报表 |
| `batch_adjust_points_dialog` | 批量调整积分 |
| `batch_adjust_by_group_dialog` | 按分组批量调整 |
| `batch_adjust_by_range_dialog` | 按范围批量调整 |
| `batch_adjust_by_role_dialog` | 按角色批量调整 |
| `delete_group_dialog` | 删除分组 |
| `show_backup_details` | 显示备份详情 |

---

## 四、界面显示 (13个)

### 刷新更新
| 功能 | 说明 |
|------|------|
| `refresh_dashboard` | 刷新仪表盘 |
| `refresh_current_tab` | 刷新当前标签 |
| `refresh_feedback_list` | 刷新反馈列表 |
| `clear_frame` | 清除框架 |

### 数据显示
| 功能 | 说明 |
|------|------|
| `show_full_dashboard` | 显示完整仪表盘 |
| `show_statistics_dashboard` | 显示统计仪表盘 |
| `show_statistics` | 显示统计 |
| `show_operation_stats` | 操作统计 |
| `show_operator_stats` | 操作员统计 |
| `show_system_trend` | 系统趋势 |
| `show_all_rankings` | 显示排行榜 |
| `show_ranking` | 显示排名 |
| `show_feedback_detail` | 反馈详情 |

---

## 五、API服务 (2个)

| 功能 | 说明 |
|------|------|
| `start_api` | 启动API服务 |
| `stop_api` | 停止API服务 |

---

## 六、安全管理 (13个)

### 权限与角色
| 功能 | 说明 |
|------|------|
| `add_admin` | 添加管理员 |
| `add_to_blacklist_dialog` | 添加黑名单 |
| `show_blacklist` | 显示黑名单 |
| `create_group_dialog` | 创建用户组 |

### 审计审批
| 功能 | 说明 |
|------|------|
| `show_audit_confirmation` | 显示审计确认 |
| `show_pending_audits` | 待审批列表 |
| `show_verification_dialog` | 验证对话框 |

### 日志与反馈
| 功能 | 说明 |
|------|------|
| `show_operation_log` | 操作日志 |
| `show_log_search` | 日志搜索 |
| `reply_feedback_dialog` | 回复反馈 |
| `view_notifications` | 查看通知 |
| `create_notification_dialog` | 创建通知 |

### 插件管理
| 功能 | 说明 |
|------|------|
| `install_plugin_dialog` | 安装插件 |
| `uninstall_plugin_dialog` | 卸载插件 |
| `toggle_plugin_dialog` | 切换插件 |

---

## 七、其他功能 (6个)

| 功能 | 说明 |
|------|------|
| `manage_tasks` | 管理任务 |
| `publish_task` | 发布任务 |
| `remote_query` | 远程查询 |

---

## 快捷键清单

### 管理员快捷键（需要权限）
| 快捷键 | 功能 |
|--------|------|
| Ctrl+S | 保存/备份 |
| Ctrl+E | 数据导出 |
| Ctrl+I | 数据导入 |
| Ctrl+N | 新建用户 |
| Ctrl+P | 积分充值 |

### 通用快捷键
| 快捷键 | 功能 |
|--------|------|
| Ctrl+R | 刷新页面 |
| F1 | 帮助 |
| F5 | 刷新数据 |

---

## 功能统计

| 分类 | 数量 |
|------|------|
| 用户管理 | 34 |
| 界面显示 | 13 |
| 安全管理 | 13 |
| 数据操作 | 10 |
| 积分管理 | 7 |
| 其他 | 3 |
| API服务 | 2 |
| **总计** | **82** |
