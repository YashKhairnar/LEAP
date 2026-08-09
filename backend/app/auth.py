from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    password_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), password_salt, 310_000, dklen=32
    )
    return password_salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, expected_hex: str) -> bool:
    _, actual_hex = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(actual_hex, expected_hex)


def new_access_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
