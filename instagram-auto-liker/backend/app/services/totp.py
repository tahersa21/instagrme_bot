"""TOTP (Time-based One-Time Password) utilities for 2FA-enabled Instagram accounts.

Workflow
────────
1. User pastes their Instagram 2FA TOTP secret (the Base32 string shown when
   they set up an authenticator app like Google Authenticator / Authy).
2. We store it encrypted with Fernet — same key used for passwords/sessions.
3. At login time (password or Playwright) we call `generate_code(secret)` to
   get the current 6-digit TOTP and inject it automatically.
4. The code auto-rotates every 30 seconds, so logins triggered within the
   valid window will always succeed without user intervention.
"""

from __future__ import annotations

import base64
import re

import pyotp


class TOTPError(Exception):
    """Raised when the TOTP secret is invalid or generation fails."""


def _normalise_secret(raw: str) -> str:
    """Strip spaces/dashes and uppercase — tolerant of copy-paste from QR apps."""
    cleaned = re.sub(r"[\s\-]", "", raw).upper()
    # Validate it's valid Base32
    try:
        base64.b32decode(cleaned, casefold=True)
    except Exception as exc:
        raise TOTPError(
            "مفتاح 2FA غير صالح — يجب أن يكون Base32 مثل: JBSWY3DPEHPK3PXP"
        ) from exc
    return cleaned


def generate_code(secret: str) -> str:
    """Return the current 6-digit TOTP code for the given secret.

    Args:
        secret: Raw or normalised Base32 TOTP secret.

    Returns:
        6-digit string e.g. "123456".

    Raises:
        TOTPError: If the secret is malformed.
    """
    normalised = _normalise_secret(secret)
    try:
        totp = pyotp.TOTP(normalised)
        return totp.now()
    except Exception as exc:
        raise TOTPError(f"فشل توليد رمز 2FA: {exc}") from exc


def validate_secret(secret: str) -> str:
    """Validate and normalise a TOTP secret. Returns the cleaned version.

    Raises:
        TOTPError: If the secret is invalid.
    """
    return _normalise_secret(secret)


def time_remaining() -> int:
    """Seconds remaining until the current TOTP window expires (0-29)."""
    import time
    return 30 - int(time.time()) % 30
