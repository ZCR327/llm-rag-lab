/**
 * Cloudflare Worker — 订阅状态 + Stripe 集成
 *
 * 端点:
 *   POST  /webhook/stripe         - Stripe webhook (更新 KV)
 *   GET   /sub?email=...          - 查订阅状态 (KV, stale 则查 Stripe)
 *   POST  /create-checkout       - 建 Stripe Checkout session, 返回 URL
 *   POST  /create-portal         - 建 Stripe Customer Portal session
 *
 * 环境变量 (Cloudflare Dashboard 或 wrangler.toml):
 *   STRIPE_SECRET_KEY        - sk_live_... 或 sk_test_...
 *   STRIPE_WEBHOOK_SECRET    - whsec_...  (用来验签 webhook)
 *   PRICE_ID_PRO             - price_...  (Pro 月费价格 ID)
 *
 * 部署:
 *   npx wrangler deploy
 *   # 然后 Dashboard 里绑 KV namespace:  wrangler kv:namespace create SUB
 *   # wrangler kv:namespace bind SUB --binding SUB
 */

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
async function verifyStripeSignature(req, env) {
  const sig = req.headers.get("stripe-signature");
  if (!sig) return false;
  const body = await req.text();
  const items = sig.split(",").reduce((acc, kv) => {
    const [k, v] = kv.split("=");
    acc[k] = v;
    return acc;
  }, {});
  const ts = items["t"];
  const v1 = items["v1"];
  if (!ts || !v1) return false;

  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(env.STRIPE_WEBHOOK_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signedPayload = `${ts}.${body}`;
  const sigBytes = await crypto.subtle.sign("HMAC", key, enc.encode(signedPayload));
  const expected = Array.from(new Uint8Array(sigBytes))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
  return expected === v1;
}

// ============ Handlers ============

async function handleWebhook(req, env, cors) {
  // 验签
  const ok = await verifyStripeSignature(req, env);
  if (!ok) return json({ error: "invalid signature" }, 400, cors);

  const event = await req.json();
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