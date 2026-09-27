"""quota.py — 免费用户每日限额管理 (v0.1.23)

模型:
- BYOK 用户: 不限 (自己掏钱)
- Pro 订阅用户: 不限 ($5/月)
- Free 用户 (默认 key): 限 10 次/天

存储: 用 session_state 计数, 每天 UTC 0 点重置
- 优点: 简单, 不需 DB
- 缺点: 同一用户清 session 就能绕 (low stakes MVP)
"""


FREE_DAILY_LIMIT = 10  # 免费用户每天 10 次


def init_quota_state():
    """初始化 session_state 里的 quota 字段. 在 app 启动时调一次."""
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


def check_can_query(has_byok: bool, is_pro: bool) -> tuple[bool, str]:
    """检查是否能查询. 返回 (allow, reason).
    allow=True: 可以查
    allow=False: 不行, reason 是给用户看的错误消息
    """
    init_quota_state()
    import streamlit as st

    if has_byok:
        return True, "BYOK"
    if is_pro:
        return True, "Pro"
    # Free tier
    if st.session_state.quota_count >= FREE_DAILY_LIMIT:
        return False, f"今天免费次数 ({FREE_DAILY_LIMIT}) 已用完. 填自己的 API key 或订阅 Pro 继续."
    return True, "free"


def increment_quota():
    """每次成功查询后调用 +1. 仅在用默认 key 时调."""
    init_quota_state()
    import streamlit as st
    st.session_state.quota_count += 1


def get_quota_status() -> dict:
    """返回 quota 当前状态 (给 UI 显示)."""
    init_quota_state()
    import streamlit as st
    return {
        "date": str(st.session_state.quota_date),
        "count": st.session_state.quota_count,
        "limit": FREE_DAILY_LIMIT,
        "remaining": max(0, FREE_DAILY_LIMIT - st.session_state.quota_count),
    }