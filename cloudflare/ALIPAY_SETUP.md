# 支付宝收款部署指南 (¥5/月 Pro 订阅)

## 前置条件 (必须先有)

- [ ] **ICP 备案域名** — 支付宝生产环境要求回调地址 `https` + 已备案。
      `*.streamlit.app` 和 `*.workers.dev` **都不行**。
      - 阿里云/腾讯云买域名：¥30-50/年
      - ICP 备案：10-20 工作日（需国内服务器 ≥3 个月）
- [ ] **支付宝开放平台账号** — https://open.alipay.com
      - 个人开发者可申请，个人资质审核约 1 工作日
- [ ] **沙箱账号** — 开放平台 → 沙箱环境 → 申请（沙箱买家/卖家账号 + 沙箱 APPID + 沙箱密钥）

---

## 一、创建应用 + 绑定产品

1. 登录 https://open.alipay.com → **控制台** → **创建应用**
   - 应用名称：`RAG Lab`
   - 应用类型：网页移动应用
   - 签名方式：**RSA2**（密钥工具下载：https://opendocs.alipay.com/open/270/105899）
2. 创建应用后 → **产品绑定** → 搜索 **「周期扣款」** → 申请签约
   - 个人资质：审核约 1 工作日
   - ⚠️ 沙箱环境需要单独在沙箱应用里绑定产品

3. **开发设置** → 配置：
   - **接口加签方式**：公钥（RSA2）
   - 粘贴 **应用公钥**（不是支付宝公钥！用支付宝开发者工具生成）
   - 拿到 **支付宝公钥**（配置后支付宝生成，复制保存）
   - **应用网关 / 授权回调地址**：`https://你的域名/alipay/notify`

---

## 二、准备密钥

用支付宝开发者工具 (https://open.alipay.com/develop/manage) 或 openssl 生成应用私钥：

```bash
# 生成 RSA2 密钥对 (2048 位)
openssl genrsa -out app_private_key.pem 2048
openssl rsa -in app_private_key.pem -pubout -out app_public_key.pem

# 提取私钥 body (去掉 PEM 头尾换行, 存成一行)
cat app_private_key.pem | grep -v '^-----' | tr -d '\n\r'
```

**需要的 3 个值**：

| 值 | 哪来的 | 格式 |
|---|---|---|
| `ALIPAY_APP_ID` | 开放平台应用页面 | `2021xxxxxxxxxxxx` |
| `ALIPAY_PRIVATE_KEY` | openssl 生成的私钥 | base64 body，**单行无换行** |
| `ALIPAY_PUBLIC_KEY` | 开放平台配置应用公钥后生成 | base64 body |

**常见坑**：
- 私钥放多行或带 `\n` → 签名失败
- 把**应用公钥**当成**支付宝公钥** → 验签全失败
- 沙箱公钥配到生产 → 验签全失败（两套密钥独立）

---

## 三、部署 Worker

```bash
cd D:\.minimax\.minimax\projects\llm-rag-lab\cloudflare

# KV (跟 Stripe 共用一个)
wrangler kv:namespace create SUB
# 把 id 填到 wrangler.toml

# 支付宝 secrets
wrangler secret put ALIPAY_APP_ID        # 2021xxxx
wrangler secret put ALIPAY_PRIVATE_KEY   # 应用私钥 base64 (单行)
wrangler secret put ALIPAY_PUBLIC_KEY    # 支付宝公钥 base64 (单行)
wrangler secret put ALIPAY_SELLER_ID     # 商户 PID (可从开放平台个人信息看)
wrangler secret put ALIPAY_NOTIFY_URL    # https://你的域名/alipay/notify

# 部署
wrangler deploy
```

---

## 四、域名配置

Worker 的默认域名 (`*.workers.dev`) 不能收支付宝通知。需要一个自己的域名：

1. 域名解析添加 CNAME：
   ```
   pay.你的域名.com  CNAME  rag-lab-billing.<sub>.workers.dev
   ```
2. Worker 绑定自定义域（Dashboard → Workers → 你的 worker → Settings → Domains → Add）
3. 域名必须 **ICP 已备案**

---

## 五、Streamlit Cloud 配置

Settings → Secrets 加：

```toml
DEEPSEEK_API_KEY = "sk-..."
ZHIPU_API_KEY = "..."
BILLING_WORKER_URL = "https://pay.你的域名.com"   # 用自定义域名, 不是 workers.dev
```

---

## 六、测试 (沙箱先行)

```bash
# 1. 本地跑 Worker
wrangler dev

# 2. 发起签约
curl -X POST http://localhost:8787/alipay/sign \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","out_trade_no":"PRO_TEST_001"}'

# 3. 用沙箱买家账号付款 (开放平台沙箱页面获取)
#    沙箱网关: https://openapidev.alipay.com/gateway.do

# 4. 查订单
curl "http://localhost:8787/alipay/query?out_trade_no=PRO_TEST_001"
```

**沙箱注意事项**：
- 周期扣款产品要**手动绑定**到沙箱应用，否则接口报"产品码无效"
- 沙箱 `notify_url` 可用 `ngrok`/`cpolar` 临时域名（不要求备案）
- 沙箱密钥和生产密钥**完全独立**，别混用

---

## 七、故障排查

| 现象 | 原因 | 解决 |
|---|---|---|
| `ACQ.INVALID_PARAMETER` 产品码无效 | 沙箱没绑周期扣款产品 | 沙箱应用配置里手动绑定 |
| 验签全失败 | 沙箱公钥配到生产 | 两套密钥独立，切换环境要同步换 |
| 签约链接打不开 | `return_url`/`notify_url` 没 HTTPS 或没备案 | 生产环境必须 https + 备案 |
| 通知收不到 | 域名没 CNAME 到 Worker | 检查 DNS 解析 |
| 通知重复到达 | 支付宝会重推直到收到 `success` | Worker 必须返回字符串 `success`（已实现） |
| 私钥签名报 `InvalidKey` | PEM 带换行/头尾 | `grep -v '^-----' \| tr -d '\n\r'` |

---

## 附：当前实现说明

`src/alipay_client.py`（Python 端）实现了完整签名逻辑，用于本地调试或 Streamlit 直接调用。

`cloudflare/alipay.js`（Worker 端）用 WebCrypto 实现，用于生产环境接通知。

**当前实现的支付方式是「单次支付」**（`alipay.trade.page.pay`，¥5.00），
不是自动续费的周期扣款 —— 原因是签约接口 `alipay.user.agreement.page.sign`
需要 SDK 模式返回 HTML 表单，Streamlit 侧不好直接渲染。

**要做到自动续费**，需要：
1. 前端引入支付宝 JS SDK
2. 调签约接口拿 `agreement_no` 存 KV
3. Worker 定时任务跑 `alipay.trade.pay` 主动扣款

如果你暂时不需要自动续费，当前版本够用（用户每次手动付 ¥5）。

如果需要，告诉我，我把 SDK 模式的前端也补上。
