"""Symmetric encryption for sensitive fields (cookies, passwords).

The master key is derived from `settings.master_key` via PBKDF2 so users can
provide a human-friendly secret in `.env`.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from ..config import get_settings


def _derive_key(master_key: str) -> bytes:
    """Derive a 32-byte Fernet key from the user-provided master key."""
    if not master_key:
        raise ValueError(
            "MASTER_KEY is empty. Set MASTER_KEY in .env to a strong random string."
        )
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        master_key.encode("utf-8"),
        salt=b"instagram-auto-liker-salt-v1",
        iterations=200_000,
        dklen=32,
    )
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_derive_key(get_settings().master_key))


def encrypt(plaintext: str) -> str:
    """Encrypt a UTF-8 string. Returns a URL-safe base64 token."""
    if plaintext is None:
        raise ValueError("Cannot encrypt None")
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """Decrypt a token previously produced by `encrypt`."""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt — wrong MASTER_KEY?") from exc
