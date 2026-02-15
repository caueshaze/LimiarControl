import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict

from app.core.config import settings


def hash_pin(pin: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100_000)
    return base64.urlsafe_b64encode(salt + key).decode("utf-8")


def verify_pin(pin: str, stored: str) -> bool:
    raw = base64.urlsafe_b64decode(stored.encode("utf-8"))
    salt, key = raw[:16], raw[16:]
    new_key = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(key, new_key)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def encode_jwt(payload: Dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_jwt(token: str) -> Dict[str, Any] | None:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError:
        return None
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected = hmac.new(settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_encode(expected), signature_b64):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None
    exp = payload.get("exp")
    if exp and isinstance(exp, int) and exp < int(time.time()):
        return None
    return payload


def build_access_token(user_id: str, username: str, ttl_seconds: int = 60 * 60 * 24) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": int(time.time()) + ttl_seconds,
    }
    return encode_jwt(payload)
