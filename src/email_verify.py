"""email_verify.py — 邮箱验证客户端

跟 Worker 通信, 实现:
- send_code(email)      发验证码
- verify(email, code)  校验
- is_verified(email)   查状态
- bind(email, client_id)  把配额跟账号绑

工作流 (用户侧):
  1. 输入邮箱 → send_code() → Worker 发阿里云邮件
  2. 输入 6 位码 → verify() → 成功
  3. bind() → 配额 key 从 IP+指纹 切换成邮箱
"""
import os
import re
import httpx

WORKER_URL = os.getenv("BILLING_WORKER_URL", "").rstrip("/")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def is_enabled() -> bool:
    return bool(WORKER_URL)


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match((email or "").strip()))


def send_code(email: str) -> tuple[bool, str]:
    """发验证码. 返回 (ok, message)."""
    if not WORKER_URL:
        return False, "验证服务未部署 (BILLING_WORKER_URL 未配置)"
    email = (email or "").strip()
    if not is_valid_email(email):
        return False, "邮箱格式不对"
    try:
        r = httpx.post(f"{WORKER_URL}/email/send-code", json={"email": email}, timeout=15.0)
        data = r.json()
        if data.get("already_verified"):
            return True, "该邮箱已验证过"
        if r.status_code != 200 or not data.get("ok"):
            return False, data.get("error", f"HTTP {r.status_code}")
        return True, f"验证码已发送到 {email} (10 分钟内有效)"
    except Exception as e:
        return False, f"发送失败: {e}"


def verify(email: str, code: str) -> tuple[bool, str]:
    """校验验证码. 返回 (verified, message)."""
    if not WORKER_URL:
        return False, "验证服务未部署"
    email = (email or "").strip()
    try:
        r = httpx.post(
            f"{WORKER_URL}/email/verify",
            json={"email": email, "code": (code or "").strip()},
            timeout=15.0,
        )
        data = r.json()
        if r.status_code != 200 or not data.get("verified"):
            return False, data.get("error", f"HTTP {r.status_code}")
        return True, "验证成功"
    except Exception as e:
        return False, f"验证失败: {e}"


def is_verified(email: str) -> bool:
    """查邮箱是否已验证."""
    if not WORKER_URL or not is_valid_email(email):
        return False
    try:
        r = httpx.get(f"{WORKER_URL}/email/check", params={"email": email.strip()}, timeout=10.0)
        return bool(r.json().get("verified"))
    except Exception:
        return False


def bind(email: str, client_id: str) -> bool:
    """把 client_id 绑到已验证邮箱 (配额跟着账号走)."""
    if not WORKER_URL or not email or not client_id:
        return False
    try:
        r = httpx.post(
            f"{WORKER_URL}/email/bind",
            json={"email": email.strip(), "client_id": client_id},
            timeout=10.0,
        )
        return r.status_code == 200
    except Exception:
        return False


def quota_key_for(email: str, client_id: str) -> str:
    """算配额 key: 已验证邮箱优先 (跟账号走), 否则用 IP+指纹."""
    if email and is_verified(email):
        return f"u:{email.strip().lower()}"
    if client_id:
        return f"c:{client_id}"
    return ""
