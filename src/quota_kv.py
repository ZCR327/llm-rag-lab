"""quota_kv.py — 配额持久化客户端 (Cloudflare Worker KV)

解决 Streamlit Cloud 的核心限制:
- session_state 存在内存, 刷新/关页面/容器重启都会清零
- 改用 Worker KV, 跨刷新/跨容器/跨重启都不丢

身份识别 (IP + 浏览器指纹 双重锁定):
- st.context.ip_address      - 用户 IP (1.45.0+)
- User-Agent                - 浏览器版本
- Accept-Language           - 语言偏好
→ 三个拼一起做 sha256 前 16 位, 作为 KV key

⚠️ 已知局限:
- 官方文档明确说 ip_address "should not be used for security measures
  because it can easily be spoofed" — 但对付普通刷量够用
- 换网络 (WiFi → 流量) / 换浏览器会算成新用户
- VPN / 代理会隐藏真实 IP
"""
import os
import hashlib
import httpx

WORKER_URL = os.getenv("BILLING_WORKER_URL", "").rstrip("/")


def is_enabled() -> bool:
    """Worker KV 是否已配置."""
    return bool(WORKER_URL)


def get_client_id() -> str:
    """算客户端唯一 ID (IP + UA + Accept-Language → sha256 前 16 位).

    拿不到任何信息时返回 "" (降级到 session_state 计数).
    """
    import streamlit as st

    # IP
    ip = ""
    try:
        ip = st.context.ip_address or ""
    except Exception:
        ip = ""

    # 浏览器指纹
    ua = ""
    lang = ""
    try:
        headers = st.context.headers
        ua = headers.get("User-Agent", "") or ""
        lang = headers.get("Accept-Language", "") or ""
    except Exception:
        pass

    if not ip and not ua:
        return ""

    raw = f"{ip}|{ua}|{lang}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_count(client_id: str) -> int:
    """查今天已用次数. Worker 不可用时返回 -1 (表示未知, 降级)."""
    if not is_enabled() or not client_id:
        return -1
    try:
        r = httpx.get(f"{WORKER_URL}/quota", params={"key": client_id}, timeout=5.0)
        r.raise_for_status()
        return int(r.json().get("count", 0))
    except Exception:
        return -1


def increment(client_id: str) -> int:
    """+1, 返回新值. 失败返回 -1."""
    if not is_enabled() or not client_id:
        return -1
    try:
        r = httpx.post(f"{WORKER_URL}/quota/incr", params={"key": client_id}, timeout=5.0)
        r.raise_for_status()
        return int(r.json().get("count", 0))
    except Exception:
        return -1


def reset(client_id: str) -> bool:
    """手动重置 (调试用)."""
    if not is_enabled() or not client_id:
        return False
    try:
        r = httpx.post(f"{WORKER_URL}/quota/reset", params={"key": client_id}, timeout=5.0)
        r.raise_for_status()
        return True
    except Exception:
        return False


def get_user_ip() -> str:
    """给 UI 显示用 (脱敏)."""
    import streamlit as st
    try:
        ip = st.context.ip_address or ""
        if ":" in ip:  # IPv6
            parts = ip.split(":")
            return ":".join(parts[:3]) + "::"
        parts = ip.split(".")
        return ".".join(parts[:2]) + ".*.*" if len(parts) >= 2 else ip
    except Exception:
        return ""
