"""alipay_client.py — 支付宝开放平台 SDK 封装 (周期扣款 / 免密支付)

功能:
- RSA2 签名 (应用私钥) / 验签 (支付宝公钥)
- 沙箱 + 生产双环境切换
- 周期扣款: 签约 → 主动扣款 → 查协议 → 解约
- 单次支付 (alipay.trade.page.pay) — 备选

环境变量 (Streamlit Cloud Secrets / wrangler secret):
  ALIPAY_APP_ID        - 应用 APPID (2021xxxxxxxxxxxx)
  ALIPAY_PRIVATE_KEY   - 应用私钥 PEM (-----BEGIN RSA PRIVATE KEY-----, 单行无换行)
  ALIPAY_PUBLIC_KEY    - 支付宝公钥 PEM
  ALIPAY_SANDBOX       - "true" 用沙箱 (默认 false = 生产)
  ALIPAY_NOTIFY_URL    - 异步通知地址 (必须 https + ICP 备案, 沙箱可放宽)
  ALIPAY_SELLER_ID     - 商户 PID (可选)

官方文档: https://open.alipay.com/development/overview
周期扣款产品申请: open.alipay.com -> 应用 -> 产品绑定 -> 周期扣款
"""
import os
import time
import json
import base64
import hashlib
import urllib.parse
import urllib.request
from typing import Optional

# 沙箱 / 生产网关
GATEWAY_SANDBOX = "https://openapidev.alipay.com/gateway.do"
GATEWAY_PROD = "https://openapi.alipay.com/gateway.do"

# 周期扣款产品码 (固定, 文档指定)
PRODUCT_CODE_CYCLE = "GENERAL_WITHHOLDING"


def _get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def is_configured() -> bool:
    """支付宝是否配置完整. 没配的话 app 降级成'显示收款码'."""
    return bool(
        _get_env("ALIPAY_APP_ID")
        and _get_env("ALIPAY_PRIVATE_KEY")
        and _get_env("ALIPAY_PUBLIC_KEY")
    )


def _gateway() -> str:
    return GATEWAY_SANDBOX if _get_env("ALIPAY_SANDBOX", "false").lower() == "true" else GATEWAY_PROD


# ============ RSA2 签名 ============

def _b64url(data: bytes) -> str:
    return base64.b64encode(data).decode().replace("\n", "")


def _build_sign_string(params: dict) -> str:
    """构造支付宝规范的签名原文 (签名和验签共用, 保证逻辑一致).

    规范 (https://open.alipay.com/doc/105540):
    - 剔除 None / "" / "sign" 三个字段
    - sign_type 保留参与签名
    - 复杂参数 (dict/list) 用紧凑 JSON 序列化 (无空格)
    - 按 key ASCII 升序, k=v& 连接
    """
    filtered = {}
    for k, v in params.items():
        if v is None or v == "" or k == "sign":
            continue
        if isinstance(v, (dict, list)):
            filtered[k] = json.dumps(v, separators=(",", ":"), ensure_ascii=False)
        else:
            filtered[k] = str(v)
    sorted_keys = sorted(filtered.keys())
    return "&".join(f"{k}={filtered[k]}" for k in sorted_keys)


def _sign(params: dict) -> str:
    """RSA2 签名: 应用私钥 SHA256withRSA, 返回 base64"""
    try:
        from Crypto.Hash import SHA256
        from Crypto.Signature import pkcs1_15
        from Crypto.PublicKey import RSA
    except ImportError:
        raise RuntimeError("缺 pycryptodome: pip install pycryptodome")

    sign_str = _build_sign_string(params)

    private_key_pem = _get_env("ALIPAY_PRIVATE_KEY")
    # 处理 PEM: 去掉头尾, 去掉所有换行/空白
    pk = private_key_pem.replace("-----BEGIN RSA PRIVATE KEY-----", "") \
                       .replace("-----END RSA PRIVATE KEY-----", "") \
                       .replace("-----BEGIN PRIVATE KEY-----", "") \
                       .replace("-----END PRIVATE KEY-----", "") \
                       .replace("\n", "").replace("\r", "").strip()
    key = RSA.import_key(base64.b64decode(pk))

    h = SHA256.new(sign_str.encode("utf-8"))
    signature = pkcs1_15.new(key).sign(h)
    return _b64url(signature)


def _verify(params: dict, sign: str) -> bool:
    """验签支付宝返回 (用支付宝公钥). 跟 _sign 共用 _build_sign_string 保证一致."""
    try:
        from Crypto.Hash import SHA256
        from Crypto.Signature import pkcs1_15
        from Crypto.PublicKey import RSA
    except ImportError:
        return False

    pub_pem = _get_env("ALIPAY_PUBLIC_KEY")
    pk = pub_pem.replace("-----BEGIN PUBLIC KEY-----", "") \
                 .replace("-----END PUBLIC KEY-----", "") \
                 .replace("-----BEGIN RSA PUBLIC KEY-----", "") \
                 .replace("-----END RSA PUBLIC KEY-----", "") \
                 .replace("\n", "").replace("\r", "").strip()
    try:
        key = RSA.import_key(base64.b64decode(pk))
    except Exception:
        return False

    sign_str = _build_sign_string(params)

    try:
        h = SHA256.new(sign_str.encode("utf-8"))
        pkcs1_15.new(key).verify(h, base64.b64decode(sign))
        return True
    except Exception:
        return False


# ============ HTTP 调用 ============

def _post(params: dict) -> dict:
    """公共请求: 补公共参数 → 签名 → POST → 解验签响应"""
    full = {
        "app_id": _get_env("ALIPAY_APP_ID"),
        "method": "",
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        **params,
    }
    full["sign"] = _sign(full)

    data = urllib.parse.urlencode(full).encode("utf-8")
    req = urllib.request.Request(_gateway(), data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except Exception as e:
        return {"error": f"请求失败: {e}"}

    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        # 网关有时返回纯文本错误
        return {"error": f"响应非 JSON: {body[:300]}"}

    # 验签 (响应里有 sign 字段时)
    sign = result.get("sign")
    if sign and not _verify(result, sign):
        result["_verify_failed"] = True
    return result


# ============ 周期扣款 API ============

def create_agreement(out_trade_no: str, amount: float, subject: str) -> dict:
    """创建签约页 URL (用户打开 → 确认协议 → 签约成功)

    amount: 元 (如 5.00)
    返回: {"url": "...", "agreement_no": "..."}  调用方跳 url
    """
    params = {
        "method": "alipay.user.agreement.page.sign",
        "biz_content": json.dumps({
            "personal_product_codes": [PRODUCT_CODE_CYCLE],
            "sign_scene": "INDUSTRY_AND_GLOBAL",
            "external_agreement_no": out_trade_no,
            "subject": subject,
            "sign_principal_type": "PRINCIPAL_TYPE",
        }, separators=(",", ":"), ensure_ascii=False),
        "notify_url": _get_env("ALIPAY_NOTIFY_URL", ""),
        "return_url": _get_env("ALIPAY_RETURN_URL", "https://llm-rag-lab.streamlit.app/"),
    }
    seller = _get_env("ALIPAY_SELLER_ID")
    if seller:
        params["biz_content"] = json.dumps({
            "personal_product_codes": [PRODUCT_CODE_CYCLE],
            "sign_scene": "INDUSTRY_AND_GLOBAL",
            "external_agreement_no": out_trade_no,
            "subject": subject,
            "sign_principal_type": "PRINCIPAL_TYPE",
            "sign_principal_id": seller,
        }, separators=(",", ":"), ensure_ascii=False)

    result = _post(params)
    # 签约接口返回的是 HTML 跳转 URL (不是 JSON), 这类走 GET
    if "error" in result:
        return result
    return result


def query_agreement(agreement_no: str, out_trade_no: str) -> dict:
    """查签约状态 (通知丢失时兜底)

    返回: {"status": "NORMAL"/"UNSIGN"/..., ...}
    """
    params = {
        "method": "alipay.user.agreement.query",
        "biz_content": json.dumps({
            "personal_product_codes": [PRODUCT_CODE_CYCLE],
            "external_agreement_no": out_trade_no,
        }, separators=(",", ":"), ensure_ascii=False),
    }
    if agreement_no:
        params["biz_content"] = json.dumps({
            "personal_product_codes": [PRODUCT_CODE_CYCLE],
            "agreement_no": agreement_no,
        }, separators=(",", ":"), ensure_ascii=False)

    return _post(params)


def withhold(agreement_no: str, out_trade_no: str, amount: float, subject: str) -> dict:
    """主动扣款 (周期扣款核心)

    amount: 元
    返回: {"trade_no": "...", "status": "SUCCESS"}
    """
    params = {
        "method": "alipay.trade.pay",
        "biz_content": json.dumps({
            "out_trade_no": out_trade_no,
            "product_code": PRODUCT_CODE_CYCLE,
            "total_amount": f"{amount:.2f}",
            "subject": subject,
            "agreement_sign_params": {
                "personal_product_code": PRODUCT_CODE_CYCLE,
                "sign_scene": "INDUSTRY_AND_GLOBAL",
            },
        }, separators=(",", ":"), ensure_ascii=False),
    }
    return _post(params)


def unsign(agreement_no: str) -> dict:
    """解约 (用户取消订阅)"""
    params = {
        "method": "alipay.user.agreement.unsign",
        "biz_content": json.dumps({
            "personal_product_codes": [PRODUCT_CODE_CYCLE],
            "agreement_no": agreement_no,
        }, separators=(",", ":"), ensure_ascii=False),
    }
    return _post(params)


# ============ 异步通知验签 ============

def verify_notify(all_params: dict) -> bool:
    """验证支付宝异步通知的签名.

    Streamlit Cloud / Worker 收到 notify_url 的 POST 时用.
    all_params: 请求里所有字段 (含 sign / sign_type)
    """
    sign = all_params.get("sign")
    if not sign:
        return False
    return _verify(all_params, sign)


def check_notify(all_params: dict) -> tuple[bool, str]:
    """校验异步通知业务状态.

    返回 (is_paid, out_trade_no)

    状态值说明:
      - TRADE_SUCCESS: 单次支付成功 (alipay.trade.page.pay)
      - SUCCESS: 通用成功 (部分产品)
      - NORMAL: 协议签约成功 (周期扣款协议状态)

    幂等要点: 支付宝通知会重发多次, 必须按 out_trade_no 去重.
    """
    if not verify_notify(all_params):
        return False, ""
    status = all_params.get("trade_status") or all_params.get("status")
    if status in ("TRADE_SUCCESS", "SUCCESS", "NORMAL"):
        return True, all_params.get("out_trade_no", "")
    return False, all_params.get("out_trade_no", "")
