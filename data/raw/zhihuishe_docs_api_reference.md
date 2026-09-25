# 积分系统 API 参考文档

## 概述

积分系统提供RESTful API接口，支持用户管理、积分操作、排行榜等功能。

**基础URL**: `http://localhost:5000/api/v1`

**认证方式**: Bearer Token 或 API Key

---

## 认证

### 登录
```
POST /api/v1/auth/login
```

**请求体**:
```json
{
    "username": "admin",
    "password": "password123"
}
```

**响应**:
```json
{
    "success": true,
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
        "id": 1,
        "username": "admin",
        "role": "super_admin"
    }
}
```

### 双因素认证验证
```
POST /api/v1/auth/verify-2fa
```

**请求体**:
```json
{
    "user_id": 1,
    "token": "123456"
}
```

---

## 用户管理

### 获取用户列表
```
GET /api/v1/users
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 (默认1) |
| limit | int | 每页数量 (默认20) |
| role | string | 角色筛选 |
| keyword | string | 关键词搜索 |

**响应**:
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "username": "user1",
            "points": 1000,
            "role": "user",
            "created_at": "2024-01-01 00:00:00"
        }
    ],
    "pagination": {
        "page": 1,
        "limit": 20,
        "total": 100
    }
}
```

### 创建用户
```
POST /api/v1/users
```

**请求体**:
```json
{
    "username": "newuser",
    "password": "password123",
    "role": "user",
    "initial_points": 100
}
```

### 更新用户
```
PUT /api/v1/users/{id}
```

**请求体**:
```json
{
    "points": 500,
    "role": "admin"
}
```

### 删除用户
```
DELETE /api/v1/users/{id}
```

---

## 积分操作

### 添加积分
```
POST /api/v1/points/add
```

**请求体**:
```json
{
    "user_id": 1,
    "points": 100,
    "reason": "每日签到奖励"
}
```

**响应**:
```json
{
    "success": true,
    "user_id": 1,
    "points_before": 100,
    "points_after": 200,
    "points_added": 100
}
```

### 减少积分
```
POST /api/v1/points/reduce
```

**请求体**:
```json
{
    "user_id": 1,
    "points": 50,
    "reason": "兑换商品"
}
```

### 积分转账
```
POST /api/v1/points/transfer
```

**请求体**:
```json
{
    "from_user_id": 1,
    "to_user_id": 2,
    "points": 100,
    "reason": "赠送"
}
```

### 查询积分
```
GET /api/v1/points/{user_id}
```

**响应**:
```json
{
    "success": true,
    "user_id": 1,
    "points": 100,
    "level": "silver",
    "last_change": {
        "points": 10,
        "reason": "每日签到",
        "time": "2024-01-01 12:00:00"
    }
}
```

---

## 排行榜

### 获取积分排行榜
```
GET /api/v1/rankings/points
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| type | string | 排行榜类型: weekly/monthly/all_time |
| limit | int | 返回数量 (默认50) |

**响应**:
```json
{
    "success": true,
    "type": "all_time",
    "rankings": [
        {
            "rank": 1,
            "user_id": 1,
            "username": "user1",
            "points": 10000,
            "level": "diamond"
        }
    ]
}
```

---

## 通知

### 发送通知
```
POST /api/v1/notifications
```

**请求体**:
```json
{
    "user_id": 1,
    "title": "积分变动通知",
    "content": "您的积分已增加100点",
    "type": "system"
}
```

### 获取通知列表
```
GET /api/v1/notifications
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | int | 用户ID |
| unread_only | bool | 只显示未读 |

---

## 数据导出

### 导出用户数据
```
GET /api/v1/export/users
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| format | string | 格式: csv/xlsx/json |

**响应**: 文件下载

### 导出积分记录
```
GET /api/v1/export/points-history
```

---

## 系统

### 健康检查
```
GET /api/v1/health
```

**响应**:
```json
{
    "status": "healthy",
    "version": "5.9",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

### 获取统计数据
```
GET /api/v1/stats
```

**响应**:
```json
{
    "success": true,
    "total_users": 1000,
    "total_points": 500000,
    "today_changes": 5000,
    "active_users": 50
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 1001 | 用户不存在 |
| 1002 | 用户已存在 |
| 1003 | 用户名格式错误 |
| 1004 | 密码格式错误 |
| 2001 | 积分不足 |
| 2002 | 积分不能为负数 |
| 3001 | 操作失败 |
| 4001 | 数据库错误 |
| 5001 | API密钥无效 |
| 5002 | API请求频率超限 |

---

## 速率限制

| 端点 | 限制 |
|------|------|
| 认证接口 | 5次/分钟 |
| 写操作 | 100次/分钟 |
| 读操作 | 200次/分钟 |
| 数据导出 | 10次/小时 |

---

## 使用示例

### cURL
```bash
# 登录
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'

# 添加积分
curl -X POST http://localhost:5000/api/v1/points/add \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"user_id": 1, "points": 100, "reason": "奖励"}'
```

### Python
```python
import requests

# 登录获取token
response = requests.post(
    'http://localhost:5000/api/v1/auth/login',
    json={'username': 'admin', 'password': 'password123'}
)
token = response.json()['token']

# 添加积分
response = requests.post(
    'http://localhost:5000/api/v1/points/add',
    headers={'Authorization': f'Bearer {token}'},
    json={'user_id': 1, 'points': 100, 'reason': '奖励'}
)
print(response.json())
```

### JavaScript
```javascript
// 登录
const loginRes = await fetch('http://localhost:5000/api/v1/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: 'admin', password: 'password123'})
});
const {token} = await loginRes.json();

// 添加积分
const addRes = await fetch('http://localhost:5000/api/v1/points/add', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({user_id: 1, points: 100, reason: '奖励'})
});
console.log(await addRes.json());
```