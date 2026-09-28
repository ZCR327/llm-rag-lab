/**
 * Cloudflare Worker — 订阅状态 + 支付集成 (Stripe + 支付宝)
 *
 * 端点:
 *   POST  /webhook/stripe         - Stripe webhook (更新 KV)
 *   GET   /sub?email=...          - 查订阅状态 (KV, stale 则查 Stripe)
 *   POST  /create-checkout       - 建 Stripe Checkout session, 返回 URL
 *   POST  /create-portal         - 建 Stripe Customer Portal session
 *   POST  /alipay/sign           - 支付宝签约/支付
 *   GET   /alipay/query          - 支付宝订单查询
 *   POST  /alipay/notify         - 支付宝异步通知 (验签 + 更新 KV)
 *
 * 环境变量 (wrangler secret put):
 *   Stripe:  STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET / PRICE_ID_PRO
 *   支付宝:  ALIPAY_APP_ID / ALIPAY_PRIVATE_KEY / ALIPAY_PUBLIC_KEY
 *            ALIPAY_SELLER_ID / ALIPAY_NOTIFY_URL
 */

import { handleAlipaySign, handleAlipayQuery, handleAlipayNotify } from "./alipay.js";
import {
  handleQuotaGet, handleQuotaIncr, handleQuotaReset, handleQuotaStats,
} from "./quota.js";
import {
  handleSendCode, handleVerify, handleCheck, handleBind,
} from "./email.js";

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (req.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      // ---- 邮箱验证 ----
      if (url.pathname === "/email/send-code" && req.method === "POST") {
        return await handleSendCode(req, env);
      }
      if (url.pathname === "/email/verify" && req.method === "POST") {
        return await handleVerify(req, env);
      }
      if (url.pathname === "/email/check" && req.method === "GET") {
        return await handleCheck(req, env, url);
      }
      if (url.pathname === "/email/bind" && req.method === "POST") {
        return await handleBind(req, env);
      }

      // ---- 配额 (IP+指纹 锁定) ----
      if (url.pathname === "/quota" && req.method === "GET") {
        return await handleQuotaGet(req, env, url);
      }
      if (url.pathname === "/quota/incr" && req.method === "POST") {
        return await handleQuotaIncr(req, env, url);
      }
      if (url.pathname === "/quota/reset" && req.method === "POST") {
        return await handleQuotaReset(req, env, url);
      }
      if (url.pathname === "/quota/stats" && req.method === "GET") {
        return await handleQuotaStats(req, env, url);
      }

      if (url.pathname === "/webhook/stripe" && req.method === "POST") {
        return await handleWebhook(req, env, corsHeaders);
      }
      if (url.pathname === "/sub" && req.method === "GET") {
        return await handleGetSubscription(req, env, corsHeaders);
      }
      if (url.pathname === "/create-checkout" && req.method === "POST") {
        return await handleCreateCheckout(req, env, corsHeaders);
      }
      if (url.pathname === "/create-portal" && req.method === "POST") {
        return await handleCreatePortal(req, env, corsHeaders);
      }

      // ---- 支付宝 ----
      if (url.pathname === "/alipay/sign" && req.method === "POST") {
        return await handleAlipaySign(req, env);
      }
      if (url.pathname === "/alipay/query" && req.method === "GET") {
        return await handleAlipayQuery(req, env, url);
      }
      if (url.pathname === "/alipay/notify" && req.method === "POST") {
        return await handleAlipayNotify(req, env);
      }

      return json({ error: "not found" }, 404, corsHeaders);
    } catch (e) {
      return json({ error: e.message, type: e.name }, 500, corsHeaders);
    }
  },
};

// ============ Tools ============
function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...extraHeaders },
  });
}

async function stripe(path, body, env) {
  const resp = await fetch(`https://api.stripe.com/v1${path}`, {
    method: body ? "POST" : "GET",
    headers: {
      "Authorization": `Bearer ${env.STRIPE_SECRET_KEY}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body ? new URLSearchParams(body).toString() : undefined,
  });
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(`Stripe API ${resp.status}: ${JSON.stringify(data)}`);
  }
  return data;
}

// 验签 Stripe webhook (v1)
// 返回 { ok, body } — body 必须先取出来, 因为 req.text() 会消费 request body
async function verifyStripeSignature(req, env) {
  const sig = req.headers.get("stripe-signature");
  if (!sig) return { ok: false, body: null };
  // 关键: 先把 body 读出来缓存, 调用方复用, 不能再调 req.json()
  const body = await req.text();
  if (!env.STRIPE_WEBHOOK_SECRET) return { ok: false, body };

  const items = sig.split(",").reduce((acc, kv) => {
    const [k, v] = kv.split("=");
    acc[k] = (acc[k] || []).concat(v);
    return acc;
  }, {});
  const ts = items["t"]?.[0];
  // Stripe 会给多个 v1 (轮换密钥期间), 任何一个匹配即可
  const v1s = items["v1"] || [];
  if (!ts || v1s.length === 0) return { ok: false, body };

  // 重放攻击防护: 时间戳超过 5 分钟直接拒
  const age = Math.abs(Math.floor(Date.now() / 1000) - parseInt(ts, 10));
  if (age > 300) return { ok: false, body };

  const enc = new TextEncoder();
  let expected;
  try {
    const key = await crypto.subtle.importKey(
      "raw",
      enc.encode(env.STRIPE_WEBHOOK_SECRET),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );
    const sigBytes = new Uint8Array(
      await crypto.subtle.sign("HMAC", key, enc.encode(`${ts}.${body}`))
    );
    expected = Array.from(sigBytes).map(b => b.toString(16).padStart(2, "0")).join("");
  } catch {
    // secret 格式异常 / 长度不对 等 — 返回 400 而不是 500
    return { ok: false, body };
  }

  // timing-safe 比较 (防时序侧信道)
  const isMatch = (a, b) => {
    if (a.length !== b.length) return false;
    let diff = 0;
    for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
    return diff === 0;
  };
  return { ok: v1s.some(v => isMatch(expected, v)), body };
}

// ============ Handlers ============

async function handleWebhook(req, env, cors) {
  // 验签 (顺带把 body 拿回来)
  const { ok, body } = await verifyStripeSignature(req, env);
  if (!ok) return json({ error: "invalid signature" }, 400, cors);

  let event;
  try {
    event = JSON.parse(body);
  } catch {
    return json({ error: "bad json" }, 400, cors);
  }
  const eventType = event.type;

  // 关注的几个事件
  if (eventType === "checkout.session.completed" ||
      eventType === "customer.subscription.created" ||
      eventType === "customer.subscription.updated" ||
      eventType === "customer.subscription.deleted") {
    const sub_or_session = event.data.object;
    const customerId = sub_or_session.customer;
    // 拿到 email
    let email = sub_or_session.customer_email || sub_or_session.customer_details?.email;
    if (!email && customerId) {
      const cust = await stripe(`/customers/${customerId}`, null, env);
      email = cust.email;
    }
    if (!email) return json({ error: "no email" }, 400, cors);

    // 写 KV
    const key = `sub:${email.toLowerCase()}`;
    const status = eventType === "customer.subscription.deleted" ? "canceled" : "active";
    const value = {
      email: email.toLowerCase(),
      customer_id: customerId,
      subscription_id: sub_or_session.id,
      status,
      current_period_end: sub_or_session.current_period_end || null,
      plan: sub_or_session.items?.data?.[0]?.price?.id || "pro",
      last_synced: Math.floor(Date.now() / 1000),
    };
    await env.SUB.put(key, JSON.stringify(value));
  }

  return json({ received: true }, 200, cors);
}

async function handleGetSubscription(req, env, cors) {
  const url = new URL(req.url);
  const email = url.searchParams.get("email");
  if (!email) return json({ error: "missing email" }, 400, cors);
  // KV 没绑 → 明确报错, 而不是 500
  if (!env.SUB) return json({ error: "KV namespace SUB not bound" }, 503, cors);

  const key = `sub:${email.toLowerCase()}`;
  const cached = await env.SUB.get(key);
  if (!cached) return json({ status: "none", email }, 200, cors);

  const data = JSON.parse(cached);
  // 检查是否过期 (>1 hour 没同步则去查 Stripe)
  const now = Math.floor(Date.now() / 1000);
  if (now - data.last_synced > 3600 && data.subscription_id && env.STRIPE_SECRET_KEY) {
    try {
      const fresh = await stripe(`/subscriptions/${data.subscription_id}`, null, env);
      data.status = fresh.status;  // active / canceled / past_due / unpaid
      data.current_period_end = fresh.current_period_end;
      data.last_synced = now;
      await env.SUB.put(key, JSON.stringify(data));
    } catch (e) {
      // Stripe 查失败, 用 cache
    }
  }

  // 检查 current_period_end
  if (data.current_period_end && data.current_period_end < now && data.status === "active") {
    data.status = "expired";
  }

  return json(data, 200, cors);
}

async function handleCreateCheckout(req, env, cors) {
  const body = await req.json().catch(() => ({}));
  const email = body.email;
  const successUrl = body.success_url || "https://llm-rag-lab.streamlit.app/?subscribed=1";
  const cancelUrl = body.cancel_url || "https://llm-rag-lab.streamlit.app/";

  if (!email) return json({ error: "missing email" }, 400, cors);

  // Pro 定价在 Stripe Dashboard 的 Price 对象上配置 (不是这里):
  //   Product: "RAG Lab Pro"  |  Recurring: 每月  |  Price: ¥5.00 CNY
  //   → unit_amount = 500 (CNY 最小单位是"分", 所以 500 = ¥5.00)
  //   → 把生成的 price_xxx ID 填到 wrangler secret put PRICE_ID_PRO
  // Stripe 会按 Price 自带的币种结算, 这里不用再传 currency
  const session = await stripe("/checkout/sessions", {
    "mode": "subscription",
    "line_items[0][price]": env.PRICE_ID_PRO,
    "line_items[0][quantity]": "1",
    "customer_email": email,
    "success_url": successUrl,
    "cancel_url": cancelUrl,
    "allow_promotion_codes": "true",
  }, env);

  return json({ url: session.url, id: session.id }, 200, cors);
}

async function handleCreatePortal(req, env, cors) {
  const body = await req.json().catch(() => ({}));
  const customerId = body.customer_id;
  if (!customerId) return json({ error: "missing customer_id" }, 400, cors);

  const portal = await stripe("/billing_portal/sessions", {
    "customer": customerId,
    "return_url": body.return_url || "https://llm-rag-lab.streamlit.app/",
  }, env);

  return json({ url: portal.url }, 200, cors);
}