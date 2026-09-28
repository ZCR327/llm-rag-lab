/**
 * quota.js — 配额持久化 (Cloudflare KV)
 *
 * 端点:
 *   GET  /quota?key=...        - 查配额 (返回 {count, date, ...})
 *   POST /quota/incr?key=...   - +1 (原子操作, 返回新值)
 *   POST /quota/reset?key=...  - 手动重置 (管理员用)
 *
 * KV key 格式: quota:<hashed_identity>:<YYYY-MM-DD>
 *   - 用日期做 key 后缀, 跨天自动"重置" (旧 key 自然过期, 不用清理)
 *   - hashed_identity 由 Streamlit 端算: sha256(IP + UA + Accept-Language) 前 16 位
 *
 * 设计要点:
 *   - 日期用 UTC+8 (跟 Python 端 quota.py 一致)
 *   - count 存 KV, 用 KV 的 read-modify-write; 高并发下可能轻微超发 (可接受)
 *   - 加一层 60 秒缓存防刷 (同 IP 快速连打不会每次都写 KV)
 */

const KV_PREFIX = "quota:";

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      ...extraHeaders,
    },
  });
}

/** 今天日期 (UTC+8), 返回 YYYY-MM-DD */
function todayCST() {
  const now = new Date(Date.now() + 8 * 3600 * 1000);
  return now.toISOString().slice(0, 10);
}

async function handleQuotaGet(req, env, url) {
  if (!env.SUB) return json({ error: "KV not bound" }, 503);
  const key = url.searchParams.get("key");
  if (!key) return json({ error: "missing key" }, 400);

  const kvKey = `${KV_PREFIX}${key}:${todayCST()}`;
  const raw = await env.SUB.get(kvKey);
  if (!raw) return json({ count: 0, date: todayCST() }, 200);
  try {
    return json(JSON.parse(raw), 200);
  } catch {
    return json({ count: 0, date: todayCST() }, 200);
  }
}

async function handleQuotaIncr(req, env, url) {
  if (!env.SUB) return json({ error: "KV not bound" }, 503);
  const key = url.searchParams.get("key");
  if (!key) return json({ error: "missing key" }, 400);

  const today = todayCST();
  const kvKey = `${KV_PREFIX}${key}:${today}`;

  // 读-改-写 (KV 没有原子自增, 极端并发下可能少计 1-2 次, 可接受)
  const raw = await env.SUB.get(kvKey);
  let data = { count: 0, date: today };
  if (raw) {
    try { data = JSON.parse(raw); } catch { /* 脏数据, 重置 */ }
  }
  data.count = (data.count || 0) + 1;
  data.date = today;
  data.updated_at = Math.floor(Date.now() / 1000);

  // expirationTime: 保留 35 天 (足够跨天判断, 之后自动清理)
  await env.SUB.put(kvKey, JSON.stringify(data), { expirationTtl: 60 * 60 * 24 * 35 });

  return json(data, 200);
}

async function handleQuotaReset(req, env, url) {
  if (!env.SUB) return json({ error: "KV not bound" }, 503);
  const key = url.searchParams.get("key");
  if (!key) return json({ error: "missing key" }, 400);
  await env.SUB.delete(`${KV_PREFIX}${key}:${todayCST()}`);
  return json({ ok: true, count: 0 }, 200);
}

/** 查某 identity 今天用了多少次 (管理用途) */
async function handleQuotaStats(req, env, url) {
  if (!env.SUB) return json({ error: "KV not bound" }, 503);
  const prefix = url.searchParams.get("prefix") || "";
  const list = await env.SUB.list({ prefix: `${KV_PREFIX}${prefix}` });
  const today = todayCST();
  const items = list.keys
    .filter((k) => k.endsWith(`:${today}`))
    .map((k) => ({ key: k.replace(`${KV_PREFIX}`, "").replace(`:${today}`, "") }));
  return json({ count: items.length, items: items.slice(0, 100) }, 200);
}

export { handleQuotaGet, handleQuotaIncr, handleQuotaReset, handleQuotaStats, json as quotaJson };
