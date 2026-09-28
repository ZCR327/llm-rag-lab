# 邮箱验证部署指南 (阿里云 DirectMail)

强制验证模式：用户必须验证邮箱才能使用 app。验证后配额**绑定账号**，换 IP / 换设备都不掉。

---

## 一、开通阿里云邮件推送

1. 登录 https://console.aliyun.com → 实名认证（个人可做）
2. 搜索「**邮件推送 DirectMail**」→ 开通（个人认证即可）
3. 免费额度：每天 200 封（够用）

---

## 二、配置发信域名

**推荐：跟 ICP 备案一起做**（省 10-20 天）

### 方案 A：有备案域名（推荐）
在 DirectMail 控制台 → 「发信域名」→ 添加你的域名，然后配 DNS：

| 类型 | 主机记录 | 记录值 |
|---|---|---|
| TXT | `_spf` | `v=spf1 include:spf.aicm.com -all` |
| TXT | `default bounce` | (控制台会给出) |
| MX | (控制台会给出) | 阿里云邮件服务器 |

> 配 SPF 是**送达率的关键**。不配的话 QQ/163 大概率进垃圾箱。

### 方案 B：没有备案域名
用阿里云提供的**默认发信地址**（如 `xxxx@service.aliyun.com`）：
- 控制台 → 「发信地址」→ 直接创建，无需配 DNS
- 缺点：发信人显示是阿里云服务地址，不够「正式」
- 送达率中等，但能用

---

## 三、拿 AccessKey

1. 阿里云控制台右上角 → 头像 → **AccessKey 管理**
2. 建议创建 **RAM 子账号**（不要用主账号密钥）：
   - 授权范围：只给 `AliyunDMSFullAccess`（或自定义最小权限）
3. 保存 `AccessKey ID` + `AccessKey Secret`

> ⚠️ AccessKey 等同于账号密码，泄露可被用来发 spam。一定用子账号 + 定期轮换。

---

## 四、部署 Worker

```bash
cd D:\.minimax\.minimax\projects\llm-rag-lab\cloudflare

# KV (跟订阅/配额共用同一个 SUB namespace)
wrangler kv:namespace create SUB
# 把 id 填到 wrangler.toml

# 邮件服务 secrets
wrangler secret put ALIDM_ACCESS_KEY_ID      # LTAI... (阿里云)
wrangler secret put ALIDM_ACCESS_KEY_SECRET  # 你的 Secret
wrangler secret put ALIDM_FROM               # 你的发信地址, 如 no-reply@yourdomain.com
wrangler secret put ALIDM_FROM_NAME          # RAG Lab (可选)

# 部署
wrangler deploy
```

---

## 五、Streamlit Cloud 配置

Settings → Secrets：

```toml
DEEPSEEK_API_KEY = "sk-..."
ZHIPU_API_KEY = "..."
BILLING_WORKER_URL = "https://rag-lab-billing.<你的子域>.workers.dev"
```

### 强制验证开关

| 变量 | 默认 | 说明 |
|---|---|---|
| `BILLING_WORKER_URL` | 空 | 不配则邮箱验证**不启用**（降级到 IP 配额）|
| `REQUIRE_EMAIL_VERIFY` | `true` | 设成 `false` 可临时关闭强制验证 |

> ⚠️ Streamlit Cloud 容器重启后 **environment secrets 不会丢**，但如果你改了代码里的默认值需要 Reboot。

---

## 六、KV 数据结构

| Key | 内容 | TTL |
|---|---|---|
| `code:<email>` | 6 位验证码 | 10 分钟 |
| `verified:<email>` | 验证标记 | 30 天（活跃用户自动续期）|
| `sendlog:<email>` | 发送频率计数 | 1 小时（限 3 封/小时）|
| `bind:<email>` | client_id 绑定 | 30 天 |
| `quota:<key>:<date>` | 每日配额计数 | 35 天 |

配额 key 优先级：
- `u:<email>` — 已验证邮箱（跟账号走）
- `c:<client_id>` — 未验证时的 IP+指纹

---

## 七、测试

```bash
# 1. 本地跑
wrangler dev

# 2. 发验证码
curl -X POST http://localhost:8787/email/send-code \
  -H "Content-Type: application/json" \
  -d '{"email":"your-test@qq.com"}'

# 3. 查是否已验证
curl "http://localhost:8787/email/check?email=your-test@qq.com"

# 4. 校验 (从邮箱里拿到 6 位码)
curl -X POST http://localhost:8787/email/verify \
  -H "Content-Type: application/json" \
  -d '{"email":"your-test@qq.com","code":"123456"}'
```

---

## 八、故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| `InvalidAccessKeyId` | AK ID/Secret 填错 | 检查 wrangler secret 是否设对 |
| `SignatureDoesNotMatch` | 签名逻辑错 | 检查 `ALIDM_*` env 是否都有（缺一个会算错）|
| `InvalidAccountName` | `ALIDM_FROM` 不是有效的发信地址 | 控制台 → 发信地址 列表里复制 |
| 邮件进垃圾箱 | 没配 SPF | 补 `_spf` TXT 记录 |
| `发送太频繁` | 1 小时内发了 3+ 次 | 等 1 小时，或清理 `sendlog:<email>` |
| `邮箱未验证` 绑不上 | 验证标记过期 (30 天) | 重新验证 |
| 配额不跟账号走 | `verified_email` 没写进 session | 检查 `st.session_state.verified_email` |

---

## 九、成本

| 项 | 费用 |
|---|---|
| 阿里云 DirectMail | 免费 200 封/天，超出 ¥0.1/封 |
| 域名 (已有备案) | ¥0 (复用) |
| 域名 (新买) | ¥30-50/年 |
| ICP 备案 | ¥0 (免费) |
| Cloudflare Worker | 免费 10 万请求/天 |
| Cloudflare KV | 免费 10 万次写入/天 |

**实际月成本**：域名 ¥3-4/月 + 邮件 ¥0（200 封/天够个人项目用）

---

## 十、用户量估算

- 每次验证 = 1 封邮件
- 每个用户验证 1 次 → 200 用户/天 免费额度内
- 配额查询：每次页面加载 1 次 KV 读 → 免费额度远超需求
