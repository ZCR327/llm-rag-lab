/**
 * email.js — 邮箱验证 (阿里云 DirectMail + KV 验证码)
 *
 * 端点:
 *   POST /email/send-code   - 生成 6 位码 → 存 KV (TTL 10min) → 发邮件
 *   POST /email/verify      - 校验验证码 → 标记邮箱已验证 (永久)
 *   GET  /email/check?email= - 查该邮箱是否已验证
 *   POST /email/bind        - 把 client_id 绑到这个已验证邮箱
 *
 * 环境变量 (wrangler secret put):
 *   ALIDM_ACCESS_KEY_ID     - 阿里云 AccessKey ID
 *   ALIDM_ACCESS_KEY_SECRET - 阿里云 AccessKey Secret
 *   ALIDM_FROM              - 发信地址 (需在 DirectMail 配置并验证)
 *   ALIDM_FROM_NAME         - 发信人显示名 (默认 RAG Lab)
 *
 * 阿里云 DirectMail API:
 *   端点: https://dm.aliyuncs.com
 *   Action: SingleSendMail
 *   签名: RPC 风格 (HMAC-SHA1, 与 AWS Signature V2 类似)
 *   文档: https://help.aliyun.com/document_detail/29414.html
 *
 * 存储:
 *   code:<email>        验证码 (TTL 600s)
 *   verified:<email>    验证标记 (TTL 30 天, 定期续期)
 *   bind:<email>        client_id 绑定 (TTL 30 天)
 *   sendlog:<email>     发送频率限制 (TTL 3600s, 防止刷邮件)
 */

// ============ 阿里云 RPC 签名 (HMAC-SHA1) ============

function percentEncode(str) {
  return encodeURIComponent(str)
    .replace(/\+/g, "%20")
    .replace(/\*/g, "%2A")
    .replace(/%7E/g, "~")
    .replace(/'/g, "%27");
}

function buildCommonParams(accessKeyId, action, format, version, signatureMethod) {
  return {
    AccessKeyId: accessKeyId,
    Action: action,
    Format: format,
    SignatureMethod: signatureMethod,
    SignatureNonce: crypto.randomUUID().replace(/-/g, ""),
    SignatureVersion: "1.0",
    Timestamp: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    Version: version,
  };
}

function percentEncodeParams(params) {
  return Object.keys(params)
    .sort()
    .map((k) => `${percentEncode(k)}=${percentEncode(params[k])}`)
    .join("&");
}

function hmacSha1(key, msg) {
  return crypto.subtle
    .importKey("raw", new TextEncoder().encode(key), { name: "HMAC", hash: "SHA-1" }, false, ["sign"])
    .then((k) => crypto.subtle.sign("HMAC", k, new TextEncoder().encode(msg)))
    .then((sig) => btoa(String.fromCharCode(...new Uint8Array(sig))));
}

async function sign(params, accessKeySecret) {
  // Step 1: 待签名串 = 排序后的 key=value&
  const stringToSign = percentEncodeParams(params) + "&";
  // Step 2: HMAC-SHA1(key = secret + "&", msg = stringToSign)
  const signature = await hmacSha1(accessKeySecret + "&", stringToSign);
  // Step 3: Base64 结果再 percentEncode
  return percentEncode(signature);
}

/** 调阿里云 OpenAPI */
async function callAliyun(env, action, version, params) {
  if (!env.ALIDM_ACCESS_KEY_ID || !env.ALIDM_ACCESS_KEY_SECRET || !env.ALIDM_FROM) {
    return { error: "阿里云邮件服务未配置 (ALIDM_ACCESS_KEY_ID / SECRET / FROM)" };
  }

  const common = buildCommonParams(
    env.ALIDM_ACCESS_KEY_ID, action, "JSON", version, "HMAC-SHA1"
  );
  const allParams = { ...common, ...params };

  allParams.Signature = await sign(allParams, env.ALIDM_ACCESS_KEY_SECRET);

  const resp = await fetch("https://dm.aliyuncs.com", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(allParams).toString(),
  });

  const text = await resp.text();
  try {
    return JSON.parse(text);
  } catch {
    return { error: `非 JSON 响应: ${text.slice(0, 300)}` };
  }
}

// ============ 工具 ============

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
  });
}

function genCode() {
  return String(Math.floor(Math.random() * 1000000)).padStart(6, "0");
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

function emailKey(prefix, email) {
  return `${prefix}:${email.toLowerCase()}`;
}

// ============ Handlers ============

/** 发验证码 */
export async function handleSendCode(req, env) {
  if (!env.SUB) return json({ error: "KV not bound" }, 503);
  const { email } = await req.json().catch(() => ({}));
  if (!email || !isValidEmail(email)) {
    return json({ error: "邮箱格式不对" }, 400);
  }
  const mail = email.toLowerCase();

  // 已经验证过就不用再发
  if (await env.SUB.get(emailKey("verified", mail))) {
    return json({ already_verified: true }, 200);
  }

  // 频率限制: 同一邮箱 1 小时内最多 3 次
  const logKey = emailKey("sendlog", mail);
  const logRaw = await env.SUB.get(logKey);
  const log = logRaw ? JSON.parse(logRaw) : { count: 0 };
  if (log.count >= 3) {
    return json({ error: "发送太频繁, 请 1 小时后再试" }, 429);
  }

  const code = genCode();
  const expiresIn = 600; // 10 分钟

  // 存验证码 (TTL 10 分钟, 自动过期)
  await env.SUB.put(
    emailKey("code", mail),
    JSON.stringify({ code, created_at: Math.floor(Date.now() / 1000) }),
    { expirationTtl: expiresIn }
  );

  // 频率计数 (TTL 1 小时)
  log.count += 1;
  log.last_at = Math.floor(Date.now() / 1000);
  await env.SUB.put(logKey, JSON.stringify(log), { expirationTtl: 3600 });

  // 发邮件
  const fromName = env.ALIDM_FROM_NAME || "RAG Lab";
  const htmlBody = `
    <div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#111">验证你的邮箱</h2>
      <p>你的验证码是:</p>
      <div style="font-size:32px;font-weight:700;letter-spacing:6px;background:#f5f5f5;padding:20px;text-align:center;border-radius:8px;margin:20px 0">
        ${code}
      </div>
      <p style="color:#666;font-size:14px">10 分钟内有效. 如果不是你自己操作, 忽略这封邮件即可.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
      <p style="color:#999;font-size:12px">RAG Lab — 本地文档 RAG + 多模态 OCR + Web Agent</p>
    </div>`;

  const resp = await callAliyun(env, "SingleSendMail", "2015-11-23", {
    AccountName: env.ALIDM_FROM,
    FromAlias: fromName,
    AddressType: "1",
    ReplyToAddress: "false",
    ToAddress: mail,
    Subject: `【RAG Lab】邮箱验证码: ${code}`,
    HtmlBody: htmlBody,
    TextBody: `你的验证码是 ${code}, 10 分钟内有效.`,
  });

  if (resp.error) {
    return json({ error: `发送失败: ${resp.error}`, detail: resp.Message || resp.Code }, 500);
  }
  if (resp.Code && resp.Code !== "OK") {
    return json({ error: `发送失败: ${resp.Message}`, code: resp.Code }, 400);
  }

  return json({ ok: true, expires_in: expiresIn }, 200);
}

/** 校验验证码 */
export async function handleVerify(req, env) {
  if (!env.SUB) return json({ error: "KV not bound" }, 503);
  const { email, code } = await req.json().catch(() => ({}));
  if (!email || !code) return json({ error: "missing email or code" }, 400);
  const mail = email.toLowerCase();

  const raw = await env.SUB.get(emailKey("code", mail));
  if (!raw) {
    return json({ verified: false, error: "验证码已过期, 请重新获取" }, 400);
  }

  const stored = JSON.parse(raw);
  if (stored.code !== String(code).trim()) {
    return json({ verified: false, error: "验证码不对" }, 400);
  }

  // 验证成功: 标记 (TTL 30 天, 用户每次使用会续期)
  await env.SUB.put(
    emailKey("verified", mail),
    JSON.stringify({
      email: mail,
      verified_at: Math.floor(Date.now() / 1000),
    }),
    { expirationTtl: 60 * 60 * 24 * 30 }
  );

  // 删掉验证码 (一次性)
  await env.SUB.delete(emailKey("code", mail));

  return json({ verified: true, email: mail }, 200);
}

/** 查是否已验证 */
export async function handleCheck(req, env, url) {
  if (!env.SUB) return json({ error: "KV not bound" }, 503);
  const email = url.searchParams.get("email");
  if (!email) return json({ error: "missing email" }, 400);
  const mail = email.toLowerCase();

  const rec = await env.SUB.get(emailKey("verified", mail));
  if (rec) {
    // 续期 (活跃用户保持验证状态)
    await env.SUB.put(emailKey("verified", mail), rec, { expirationTtl: 60 * 60 * 24 * 30 });
    return json({ verified: true, email: mail }, 200);
  }
  return json({ verified: false, email: mail }, 200);
}

/**
 * 绑定 client_id → 已验证邮箱
 * 让配额跟账号走 (换 IP / 换浏览器都不掉)
 */
export async function handleBind(req, env) {
  if (!env.SUB) return json({ error: "KV not bound" }, 503);
  const { email, client_id } = await req.json().catch(() => ({}));
  if (!email || !client_id) return json({ error: "missing email or client_id" }, 400);
  const mail = email.toLowerCase();

  // 只有已验证的邮箱才能绑
  if (!(await env.SUB.get(emailKey("verified", mail)))) {
    return json({ error: "邮箱未验证" }, 403);
  }

  await env.SUB.put(
    emailKey("bind", mail),
    JSON.stringify({
      email: mail,
      client_id,
      bound_at: Math.floor(Date.now() / 1000),
    }),
    { expirationTtl: 60 * 60 * 24 * 30 }
  );

  return json({ ok: true, email: mail, client_id }, 200);
}

/** 反查: client_id → 已绑定的邮箱 */
export async function handleUnbind(req, env) {
  if (!env.SUB) return json({ error: "KV not bound" }, 503);
  const { client_id } = await req.json().catch(() => ({}));
  if (!client_id) return json({ error: "missing client_id" }, 400);

  // KV 不能反查, 所以由 Python 端缓存映射 (调用时带上 email)
  return json({ ok: true }, 200);
}
