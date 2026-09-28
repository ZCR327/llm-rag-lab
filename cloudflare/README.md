# Cloudflare Worker + KV 订阅服务

## 架构

```
用户  ─→  Streamlit Cloud  ─→  Cloudflare Worker  ─→  Stripe API
                │                     │
                │                     └──→  Cloudflare KV (订阅状态)
                │
                └──→  DeepSeek / 智谱 API (RAG + OCR)
```

## 一、Cloudflare 准备

### 1. 注册账号 + 创建 Worker

```bash
# 安装 wrangler
npm install -g wrangler

# 登录 (会打开浏览器)
wrangler login

# 创建项目
wrangler init rag-lab-billing --type javascript
```

### 2. 创建 KV namespace

```bash
wrangler kv:namespace create SUB
# 输出: id = "abc123..."
wrangler kv:namespace create SUB --preview
# 输出: preview_id = "def456..."
```

把 `id` 和 `preview_id` 填到 `wrangler.toml` 的 `kv_namespaces` 块（取消注释）。

### 3. 设置 Secrets（不会写进 git）

```bash
wrangler secret put STRIPE_SECRET_KEY
# 粘贴: sk_test_... 或 sk_live_...

wrangler secret put STRIPE_WEBHOOK_SECRET
# 粘贴: whsec_... (Stripe Dashboard → Webhooks → endpoint secret)

wrangler secret put PRICE_ID_PRO
# 粘贴: price_... (Stripe Dashboard → Products → 创建月费订阅产品, 复制 Price ID)
```

### 4. 部署

```bash
wrangler deploy
# 输出: Published rag-lab-billing (X.XX sec)
# Worker URL: https://rag-lab-billing.<你的子域名>.workers.dev
```

## 二、Stripe 准备

### 1. 注册 + 测试模式

- https://dashboard.stripe.com/register (推荐先 test mode)
- 测试 key: `sk_test_...` (Dashboard → Developers → API keys)
- 测试 webhook secret: 需要先创建 webhook endpoint (见下)

### 2. 创建订阅产品

- Dashboard → Products → **Add product**
- Name: "RAG Lab Pro"
- Pricing model: **Recurring** (每月)
- Price: **¥5.00 CNY** (currency 选 CNY / 人民币)
  - unit_amount = 500 (CNY 最小单位是"分")
  - ⚠️ Stripe 账户必须支持 CNY 结算, 否则只能选 USD (改 `¥5` → `$5`)
- Save → 复制 `price_...` ID → 填到 `wrangler secret put PRICE_ID_PRO`

### 3. 配置 Webhook

- Dashboard → Developers → Webhooks → **Add endpoint**
- URL: `https://rag-lab-billing.<子域>.workers.dev/webhook/stripe`
- Events to send:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- Save → 展开 → 复制 **Signing secret** (`whsec_...`) → 填到 `wrangler secret put STRIPE_WEBHOOK_SECRET`

## 三、Streamlit 配置

在 Streamlit Cloud → Settings → Secrets 加：

```toml
DEEPSEEK_API_KEY = "sk-..."
ZHIPU_API_KEY = "..."
BILLING_WORKER_URL = "https://rag-lab-billing.<子域>.workers.dev"
```

更新 `src/billing.py` 的 `WORKER_URL` 默认值 OR 通过 env 覆盖。

## 四、测试

```bash
# 本地测试 Worker
wrangler dev

# 模拟 webhook (用 Stripe CLI)
stripe trigger checkout.session.completed
# 应该在 KV 里看到新订阅

# 查订阅状态
curl 'http://localhost:8787/sub?email=test@example.com'
# 应该返回 {"status": "active", ...}
```

## 五、上线后

切换到 live mode：
1. Stripe Dashboard → 切换到 **Live** → 重新生成 API key (`sk_live_...`)
2. 重新创建产品（live mode 下）
3. 更新 Worker secrets
4. 重新部署
5. 把 BILLING_WORKER_URL 改成 live 的 Worker URL

## 故障排查

| 现象 | 排查 |
|---|---|
| Worker 部署后 404 | 检查 `main` 路径 = "worker.js" |
| /sub 返回 "missing email" | URL 加 `?email=...` |
| Webhook 不更新 KV | Stripe Dashboard → Webhooks → 看最近请求的 HTTP 状态 |
| `invalid signature` | `STRIPE_WEBHOOK_SECRET` 没设或跟 Stripe Dashboard 不一致 |
| 创建 Checkout 报 400 | `PRICE_ID_PRO` 不存在或账号 currency 不匹配 |