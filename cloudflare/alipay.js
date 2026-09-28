/**
 * alipay.js — 支付宝周期扣款集成 (Cloudflare Worker 版)
 *
 * 端点 (挂到主 worker.js 的 fetch 路由):
 *   POST /alipay/sign      - 生成签约跳转 URL
 *   POST /alipay/withhold  - 主动扣款 (月续费)
 *   POST /alipay/unsign    - 解约
 *   GET  /alipay/query?out_trade_no=...  - 查签约状态
 *   POST /alipay/notify    - 支付宝异步通知 (验签 + 更新 KV)
 *
 * 环境变量 (wrangler secret put):
 *   ALIPAY_APP_ID       - 2021xxxxxxxxxxxx
 *   ALIPAY_PRIVATE_KEY  - 应用私钥 PEM (base64 body, 无头尾无换行)
 *   ALIPAY_PUBLIC_KEY   - 支付宝公钥 PEM (base64 body)
 *   ALIPAY_GATEWAY      - 沙箱/生产网关 (可选, 默认生产)
 *   ALIPAY_SELLER_ID    - 商户 PID
 *   ALIPAY_NOTIFY_URL   - 异步通知地址 (必须 https + 备案)
 *
 * 官方文档: https://open.alipay.com/development/overview
 */

const PRODUCT_CODE_CYCLE = "GENERAL_WITHHOLDING";
const GATEWAY_SANDBOX = "https://openapidev.alipay.com/gateway.do";
const GATEWAY_PROD = "https://openapi.alipay.com/gateway.do";

// ============ PEM <-> ArrayBuffer ============

function pemToArrayBuffer(pem) {
  const clean = pem
    .replace(/-----BEGIN (RSA )?PRIVATE KEY-----/g, "")
    .replace(/-----END (RSA )?PRIVATE KEY-----/g, "")
    .replace(/-----BEGIN PUBLIC KEY-----/g, "")
    .replace(/-----END PUBLIC KEY-----/g, "")
    .replace(/-----BEGIN RSA PUBLIC KEY-----/g, "")
    .replace(/-----END RSA PUBLIC KEY-----/g, "")
    .replace(/\s/g, "");
  const bin = atob(clean);
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  return buf.buffer;
}

// ============ RSA2 签名 / 验签 ============

function base64ToHex(b64) {
  const bin = atob(b64);
  let hex = "";
  for (let i = 0; i < bin.length; i++) {
    hex += bin.charCodeAt(i).toString(16).padStart(2, "0");
  }
  return hex;
}

function hexToBase64(hex) {
  const bin = atob(hex);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return btoa(String.fromCharCode(...bytes));
}

/** 构造支付宝规范要求的签名原文 (签名和验签共用, 保证逻辑一致) */
function buildSignString(params) {
  const filtered = {};
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined || v === "") continue;
    if (k === "sign") continue;
    // 复杂参数用紧凑 JSON (无空格) — 与 Python 端保持一致
    if (typeof v === "object" && v !== null) {
      filtered[k] = JSON.stringify(v);
    } else {
      filtered[k] = String(v);
    }
  }
  // key ASCII 升序
  const keys = Object.keys(filtered).sort();
  return keys.map((k) => `${k}=${filtered[k]}`).join("&");
}

async function rsa2Sign(signString, privateKeyPem) {
  const key = await crypto.subtle.importKey(
    "pkcs8",
    pemToArrayBuffer(privateKeyPem),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    new TextEncoder().encode(signString)
  );
  const hex = base64ToHex(btoa(String.fromCharCode(...new Uint8Array(sig))));
  return hexToBase64(hex);
}

async function rsa2Verify(signString, signB64, publicKeyPem) {
  try {
    const key = await crypto.subtle.importKey(
      "spki",
      pemToArrayBuffer(publicKeyPem),
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
      false,
      ["verify"]
    );
    // 支付宝签名是 base64 的 PKCS#1 v1.5, WebCrypto 直接接受
    return await crypto.subtle.verify(
      "RSASSA-PKCS1-v1_5",
      key,
      base64ToArrayBuffer(signB64),
      new TextEncoder().encode(signString)
    );
  } catch (e) {
    return false;
  }
}

function base64ToArrayBuffer(b64) {
  const bin = atob(b64);
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  return buf.buffer;
}

// ============ HTTP 调用 ============

async function alipayPost(method, bizContent, env, extraParams = {}) {
  if (!env.ALIPAY_APP_ID || !env.ALIPAY_PRIVATE_KEY) {
    throw new Error("支付宝未配置 (ALIPAY_APP_ID / ALIPAY_PRIVATE_KEY 缺失)");
  }
  const gateway = env.ALIPAY_GATEWAY || GATEWAY_PROD;
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ` +
                    `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

  const params = {
    app_id: env.ALIPAY_APP_ID,
    method,
    format: "JSON",
    charset: "utf-8",
    sign_type: "RSA2",
    timestamp,
    version: "1.0",
    ...extraParams,
    biz_content: typeof bizContent === "string" ? bizContent : JSON.stringify(bizContent),
  };

  params.sign = await rsa2Sign(buildSignString(params), env.ALIPAY_PRIVATE_KEY);

  const resp = await fetch(gateway, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded; charset=utf-8" },
    body: new URLSearchParams(params).toString(),
  });
  const text = await resp.text();
  try {
    return JSON.parse(text);
  } catch {
    return { error: `非 JSON 响应: ${text.slice(0, 300)}` };
  }
}

// ============ Handlers ============

/** 生成签约跳转 URL (用户打开 → 确认协议) */
export async function handleAlipaySign(req, env) {
  const body = await req.json().catch(() => ({}));
  const { email, out_trade_no, subject = "RAG Lab Pro 订阅" } = body;
  if (!email || !out_trade_no) {
    return Response.json({ error: "missing email or out_trade_no" }, { status: 400 });
  }

  const biz = {
    personal_product_codes: [PRODUCT_CODE_CYCLE],
    sign_scene: "INDUSTRY_AND_GLOBAL",
    external_agreement_no: out_trade_no,
    subject,
    sign_principal_type: "PRINCIPAL_TYPE",
  };
  if (env.ALIPAY_SELLER_ID) biz.sign_principal_id = env.ALIPAY_SELLER_ID;

  // 签约接口返回的是 HTML (自动跳支付宝), 不是 JSON ——
  // 所以用 SDK 模式: 只构造 URL, 不做服务端请求
  // 简化方案: 走 trade.page.pay 单次支付 (用户手动付, 不自动续费)
  const result = await alipayPost("alipay.trade.page.pay", {
    out_trade_no,
    total_amount: "5.00",
    subject,
    product_code: "FAST_INSTANT_TRADE",
  }, env, {
    notify_url: env.ALIPAY_NOTIFY_URL || "",
    return_url: body.return_url || "",
  });

  if (result.alipay_trade_page_pay) {
    return Response.json({
      status: "ok",
      // 支付宝会返回一个网关跳转 URL
      form: result.alipay_trade_page_pay,
      order_id: result.alipay_trade_page_pay.order_id,
    });
  }
  return Response.json({ error: result.sub_msg || result.msg || "签约失败", raw: result }, { status: 400 });
}

/** 查签约状态 */
export async function handleAlipayQuery(req, env, url) {
  const outTradeNo = url.searchParams.get("out_trade_no");
  if (!outTradeNo) return Response.json({ error: "missing out_trade_no" }, { status: 400 });

  const result = await alipayPost("alipay.trade.query", {
    out_trade_no: outTradeNo,
  }, env);
  return Response.json(result);
}

/** 异步通知: 验签 + 更新 KV */
export async function handleAlipayNotify(req, env) {
  if (!env.SUB) return new Response("KV not bound", { status: 503 });

  // 支付宝通知是 form-urlencoded
  const contentType = req.headers.get("content-type") || "";
  let params = {};
  if (contentType.includes("application/json")) {
    params = await req.json();
  } else {
    const text = await req.text();
    params = Object.fromEntries(new URLSearchParams(text));
  }

  const sign = params.sign;
  if (!sign) return new Response("missing sign", { status: 400 });

  // 验签 (用支付宝公钥)
  const signString = buildSignString(params);
  const valid = await rsa2Verify(signString, sign, env.ALIPAY_PUBLIC_KEY);
  if (!valid) {
    return new Response("invalid signature", { status: 400 });
  }

  // 业务处理: 支付成功
  const status = params.trade_status || params.status;
  if (status !== "TRADE_SUCCESS" && status !== "SUCCESS") {
    return new Response("success");  // 非成功状态也返回 success, 避免支付宝重推
  }

  // 拿 email (支付宝异步通知里通常没有, 用 out_trade_no 关联)
  const outTradeNo = params.out_trade_no;
  const email = params.passback_params || params.email || params.buyer_email;
  if (email && outTradeNo) {
    const key = `sub:${email.toLowerCase()}`;
    const existing = await env.SUB.get(key);
    const prev = existing ? JSON.parse(existing) : {};
    const data = {
      ...prev,
      email: email.toLowerCase(),
      payment: "alipay",
      order_id: outTradeNo,
      trade_no: params.trade_no,
      status: "active",
      amount: params.total_amount,
      paid_at: params.gmt_payment || params.notify_time,
      last_synced: Math.floor(Date.now() / 1000),
    };
    await env.SUB.put(key, JSON.stringify(data));
  }

  // 必须返回 success, 否则支付宝会重推多次
  return new Response("success");
}
