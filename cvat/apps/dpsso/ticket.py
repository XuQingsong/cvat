"""HMAC 票据校验（与 data-pipeline Portal BFF 签发侧共享密钥与格式）。

格式：dpsso1.<b64url(payload_json)>.<b64url(hmac_sha256)>
payload: {"uid","name","email","roles":[...],"exp":unix,"nonce","next"}
密钥经 env DP_SSO_SECRET 注入；票据 60s 有效、nonce 一次性（redis cache.add）。
"""
import base64
import hashlib
import hmac
import json
import time


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64ud(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class TicketError(Exception):
    """票据校验失败（签名/过期/重放/格式）。"""


def sign_ticket(secret: str, payload: dict) -> str:
    """签发（BFF 侧同算法；本侧仅用于测试与文档化）。"""
    body = _b64u(json.dumps(payload, separators=(",", ":")).encode())
    head = f"dpsso1.{body}"
    sig = _b64u(hmac.new(secret.encode(), head.encode(), hashlib.sha256).digest())
    return f"{head}.{sig}"


def verify_ticket(secret: str, ticket: str, now: float | None = None) -> dict:
    """校验签名 + 过期；返回 payload。不消费 nonce（调用方负责单次性）。"""
    parts = ticket.split(".")
    if len(parts) != 3 or parts[0] != "dpsso1":
        raise TicketError("bad ticket format")
    head = f"{parts[0]}.{parts[1]}"
    try:
        sig = _b64ud(parts[2])
    except Exception as e:  # noqa: BLE001 — b64 解码异常归并为 TicketError
        raise TicketError("bad signature encoding") from e
    want = hmac.new(secret.encode(), head.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(sig, want):
        raise TicketError("signature mismatch")
    try:
        payload = json.loads(_b64ud(parts[1]))
    except Exception as e:  # noqa: BLE001
        raise TicketError("bad payload") from e
    if not isinstance(payload, dict) or not payload.get("uid"):
        raise TicketError("payload missing uid")
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or exp < (now or time.time()):
        raise TicketError("ticket expired")
    if not payload.get("nonce"):
        raise TicketError("payload missing nonce")
    return payload
