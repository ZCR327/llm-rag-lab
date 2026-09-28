"""quota.py — 每日限额管理 (v0.1.24)

模型 (v0.1.24 改: Pro 从"不限"改为"每天 100 次"):
- BYOK 用户: 不限 (自己掏钱, 用自己的 key)
- Pro 订阅用户: ¥5/月, 每天 100 次 (每天重置)
- Free 用户 (默认 key): 每天 10 次 (每天重置)

存储: 用 session_state 计数, 每天 UTC+8 0 点重置
- 优点: 简单, 不需 DB
- 缺点: 同一用户清 session 就能绕 (low stakes MVP, 后续可换 Worker KV)
"""


FREE_DAILY_LIMIT = 10     # 免费用户: 每天 10 次
PRO_DAILY_LIMIT = 100     # Pro 用户: 每天 100 次 (v0.1.24 新增)

# 定价 (展示用)
PRICING_LABEL = {
    "free": "免费 (每天 10 次)",
    "pro": "Pro ¥5/月 (每天 100 次)",
    "byok": "自带 Key (不限次)",
}


def get_daily_limit(is_pro: bool) -> int:
    """按用户类型返回每日限额."""
    return PRO_DAILY_LIMIT if is_pro else FREE_DAILY_LIMIT


def init_quota_state():
    """初始化 session_state 里的 quota 字段. 每次检查前都调 (幂等)."""
    import streamlit as st
    from datetime import datetime, timezone, timedelta

    # 用 UTC+8 (中国时区) 做日期分界
    tz_china = timezone(timedelta(hours=8))
    today = datetime.now(tz_china).date()

    if "quota_date" not in st.session_state:
        st.session_state.quota_date = today
        st.session_state.quota_count = 0

    # 新的一天 → 重置计数
    if st.session_state.quota_date != today:
        st.session_state.quota_date = today
        st.session_state.quota_count = 0


def get_quota_key() -> str:
    """算当前用户的配额 key.

    优先级:
    1. 已验证邮箱  → "u:<email>"  (跟账号走, 换 IP / 换浏览器都不掉)
    2. IP + 指纹   → "c:<client_id>" (未验证时的临时身份)
    3. 空字符串    → 降级 session_state

    已验证邮箱存在 st.session_state["verified_email"] 里 (由 email_verify 设置).
    """
    import streamlit as st

    verified_email = st.session_state.get("verified_email")
    if verified_email:
        return f"u:{verified_email.strip().lower()}"

    try:
        import quota_kv
        cid = quota_kv.get_client_id()
        if cid:
            return f"c:{cid}"
    except Exception:
        pass
    return ""


def _get_count() -> int:
    """取今天已用次数. 优先 Worker KV (跨刷新/跨重启), 降级 session_state."""
    import streamlit as st

    try:
        import quota_kv
        if quota_kv.is_enabled():
            key = get_quota_key()
            if key:
                n = quota_kv.get_count(key)
                if n >= 0:
                    return n
    except Exception:
        pass
    return st.session_state.get("quota_count", 0)


def _add_count() -> int:
    """+1 并返回新值. 优先 Worker KV, 降级 session_state."""
    import streamlit as st

    try:
        import quota_kv
        if quota_kv.is_enabled():
            key = get_quota_key()
            if key:
                n = quota_kv.increment(key)
                if n >= 0:
                    # 同步到 session_state (给 UI 显示用, 避免重复请求)
                    st.session_state.quota_count = n
                    return n
    except Exception:
        pass
    st.session_state.quota_count = st.session_state.get("quota_count", 0) + 1
    return st.session_state.quota_count


def check_can_query(has_byok: bool, is_pro: bool) -> tuple[bool, str]:
    """检查是否能查询. 返回 (allow, reason).

    优先级: BYOK > Pro > Free
    - BYOK: 永远允许 (用用户自己的 key, 不消耗平台额度)
    - Pro: 每天 100 次
    - Free: 每天 10 次
    """
    init_quota_state()
    import streamlit as st

    if has_byok:
        return True, "BYOK"

    limit = get_daily_limit(is_pro)
    count = _get_count()
    if count >= limit:
        if is_pro:
            return False, (
                f"今天 Pro 次数 ({limit}) 已用完, 明天 0 点重置. "
                f"或填自己的 API Key (不限次)."
            )
        return False, (
            f"今天免费次数 ({limit}) 已用完. "
            f"填自己的 API Key (不限次) 或订阅 Pro (¥5/月, 每天 {PRO_DAILY_LIMIT} 次)."
        )
    return True, "pro" if is_pro else "free"


def increment_quota():
    """每次成功查询后调用 +1. 仅在用平台默认 key 时调 (BYOK 不计)."""
    init_quota_state()
    _add_count()


def get_quota_status(is_pro: bool = False) -> dict:
    """返回 quota 当前状态 (给 UI 显示)."""
    init_quota_state()
    import streamlit as st
    limit = get_daily_limit(is_pro)
    count = _get_count()
    # 标识当前用的是哪种存储 (UI 上提示用户)
    storage = "session"
    try:
        import quota_kv
        if quota_kv.is_enabled():
            key = get_quota_key()
            if key:
                storage = "account" if key.startswith("u:") else "kv"
    except Exception:
        pass
    return {
        "date": str(st.session_state.quota_date),
        "count": count,
        "limit": limit,
        "remaining": max(0, limit - count),
        "is_pro": is_pro,
        "tier": "pro" if is_pro else "free",
        "storage": storage,
        "key_type": "email" if storage == "account" else ("ip" if storage == "kv" else "memory"),
    }
