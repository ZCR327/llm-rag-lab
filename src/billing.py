"""billing.py — Cloudflare Worker 客户端, 查询/创建 Stripe 订阅"""
import os
import json
import httpx

WORKER_URL = os.getenv("BILLING_WORKER_URL", "https://rag-lab-billing.xiaomi-minimax.workers.dev")


def check_subscription(email: str) -> dict:
    """查用户的订阅状态. 返回 {status, customer_id, current_period_end, plan}.

    status: 'none' (没订阅) / 'active' (订阅中) / 'canceled' (已取消) / 'expired' (过期)
    """
    try:
        r = httpx.get(f"{WORKER_URL}/sub", params={"email": email}, timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


def create_checkout(email: str, success_url: str = None, cancel_url: str = None) -> str:
    """建 Stripe Checkout session, 返回跳转 URL. 用户打开 URL 完成支付."""
    body = {"email": email}
    if success_url:
        body["success_url"] = success_url
    if cancel_url:
        body["cancel_url"] = cancel_url
    try:
        r = httpx.post(f"{WORKER_URL}/create-checkout", json=body, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        return data.get("url", "")
    except Exception as e:
        return f"(error: {e})"


def create_portal(customer_id: str, return_url: str = None) -> str:
    """建 Stripe Customer Portal session, 返回跳转 URL. 用户管理订阅/取消."""
    body = {"customer_id": customer_id}
    if return_url:
        body["return_url"] = return_url
    try:
        r = httpx.post(f"{WORKER_URL}/create-portal", json=body, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        return data.get("url", "")
    except Exception as e:
        return f"(error: {e})"