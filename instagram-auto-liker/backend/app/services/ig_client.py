"""Thin wrapper around `instagrapi` to abstract login + media fetching.

Anti-detection layer
────────────────────
- Each account gets a **stable unique Android device fingerprint** stored inside
  the encrypted session (device_id, uuid, phone_id, ad_id, build_id, etc.).
  instagrapi generates this automatically on first login and re-uses it on
  restore_client() so Instagram always "sees" the same phone.

- An optional per-account **proxy** (http/socks5) is applied to every Client
  instance, ensuring each account appears from a different IP.

- The internal `cl.delay_range` adds small jitter to every private API call.
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests as _requests

from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    ChallengeRequired,
    LoginRequired,
    PleaseWaitFewMinutes,
    TwoFactorRequired,
)

from ..models import Account
from . import crypto

logger = logging.getLogger(__name__)


class IGClientError(Exception):
    """Base error from IG client wrapper."""


class IGChallengeRequired(IGClientError):
    pass


class IG2FARequired(IGClientError):
    pass


class IGBadPassword(IGClientError):
    pass


class IGRateLimited(IGClientError):
    pass


# ─── client factory ───────────────────────────────────────────────────────────

def _new_client(proxy: str | None = None) -> Client:
    """Create a fresh instagrapi Client with optional proxy and realistic jitter."""
    cl = Client()
    # Randomise the internal API call delay (0.5 – 2.5 s) to avoid clockwork patterns
    cl.delay_range = [
        round(random.uniform(0.5, 1.5), 2),
        round(random.uniform(1.5, 2.5), 2),
    ]
    if proxy:
        try:
            cl.set_proxy(proxy)
            logger.info("Proxy applied: %s", _mask_proxy(proxy))
        except Exception as exc:
            logger.warning("Failed to apply proxy %s: %s", _mask_proxy(proxy), exc)
    return cl


def _mask_proxy(proxy: str) -> str:
    """Return a credential-free proxy string safe for logging."""
    try:
        p = urlparse(proxy)
        masked = p._replace(netloc=f"***:***@{p.hostname}:{p.port}")
        return urlunparse(masked)
    except Exception:
        return "***"


# ─── login helpers ────────────────────────────────────────────────────────────

def login_with_password(
    username: str,
    password: str,
    verification_code: str | None = None,
    proxy: str | None = None,
) -> tuple[Client, dict[str, Any]]:
    """Log in via username + password. Returns (client, session_settings_dict)."""
    cl = _new_client(proxy)
    try:
        cl.login(username, password, verification_code=verification_code or "")
    except TwoFactorRequired as exc:
        raise IG2FARequired("Two-factor code required") from exc
    except BadPassword as exc:
        raise IGBadPassword("Invalid username or password") from exc
    except ChallengeRequired as exc:
        raise IGChallengeRequired("Instagram requires a challenge / verification") from exc
    except PleaseWaitFewMinutes as exc:
        raise IGRateLimited("Instagram asked us to wait a few minutes") from exc
    except _requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        if status == 400:
            raise IGClientError(
                "Instagram رفض تسجيل الدخول (400). قد يكون الحساب محميًا أو يتطلب "
                "تحقق إضافي. جرّب تسجيل الدخول عبر المتصفح أولًا ثم استخدم الكوكيز."
            ) from exc
        raise IGClientError(f"Instagram HTTP error {status}") from exc
    except Exception as exc:
        raise IGClientError(f"Instagram login failed: {exc}") from exc
    return cl, cl.get_settings()


def login_with_cookies(
    username: str,
    cookies_json: str,
    proxy: str | None = None,
) -> tuple[Client, dict[str, Any]]:
    """Log in by importing a previously exported session/cookies JSON."""
    cl = _new_client(proxy)
    try:
        data = json.loads(cookies_json)
    except json.JSONDecodeError as exc:
        raise IGClientError("cookies_json is not valid JSON") from exc

    if isinstance(data, dict) and "authorization_data" in data:
        cl.set_settings(data)
    elif isinstance(data, dict) and "cookies" in data:
        cl.set_settings(data)
    elif isinstance(data, list):
        cookies = {c["name"]: c["value"] for c in data if "name" in c and "value" in c}
        sessionid = cookies.get("sessionid")
        if not sessionid:
            raise IGClientError("Cookies must contain a `sessionid` entry")
        cl.login_by_sessionid(sessionid)
    else:
        raise IGClientError("Unsupported cookies/session format")

    try:
        cl.username = username
        cl.account_info()
    except LoginRequired as exc:
        raise IGClientError("Session expired — please re-login") from exc

    return cl, cl.get_settings()


def restore_client(account: Account) -> Client:
    """Rebuild a Client from the encrypted session (+ optional proxy) on `account`."""
    if not account.encrypted_session:
        raise IGClientError(f"No saved session for account {account.username}")

    proxy: str | None = None
    if account.encrypted_proxy:
        try:
            proxy = crypto.decrypt(account.encrypted_proxy)
        except Exception as exc:
            logger.warning("Failed to decrypt proxy for %s: %s", account.username, exc)

    settings_dict = json.loads(crypto.decrypt(account.encrypted_session))
    cl = _new_client(proxy)
    # Restore the same device fingerprint that was created at first login
    cl.set_settings(settings_dict)
    cl.username = account.username
    return cl


def login_with_playwright_session(
    username: str,
    cookies: list[dict],
    proxy: str | None = None,
) -> tuple[Client, dict[str, Any]]:
    """Build an instagrapi session from cookies extracted by Playwright.

    Playwright gives us real browser cookies — we find the sessionid and
    hand it to instagrapi's login_by_sessionid() which trusts it as a
    legitimate browser session.
    """
    cl = _new_client(proxy)

    sessionid: str | None = None
    for c in cookies:
        if c.get("name") == "sessionid":
            sessionid = c["value"]
            break

    if not sessionid:
        raise IGClientError("لم يتم العثور على sessionid في كوكيز المتصفح")

    try:
        cl.login_by_sessionid(sessionid)
        cl.username = username
        cl.account_info()   # validates the session is alive
    except LoginRequired as exc:
        raise IGClientError("الجلسة منتهية أو غير صالحة — أعد تسجيل الدخول") from exc
    except Exception as exc:
        raise IGClientError(f"فشل التحقق من الجلسة: {exc}") from exc

    return cl, cl.get_settings()


def session_to_encrypted_blob(settings_dict: dict[str, Any]) -> str:
    return crypto.encrypt(json.dumps(settings_dict))


# ─── automatic re-login ───────────────────────────────────────────────────────

def relogin_account(account: "Account", db: "Any") -> Client:
    """Attempt automatic re-login using the stored encrypted password + TOTP.

    On success the function:
    - Updates ``account.encrypted_session`` with the fresh session blob.
    - Sets ``account.last_login_at`` and ``account.session_renewed_at`` to now.
    - Marks ``account.is_active = True`` and clears ``account.last_error``.
    - Commits the changes to *db*.

    Returns the freshly authenticated :class:`Client`.

    Raises:
        IGClientError: When no password is stored, or when the login attempt
            fails (bad password, challenge, rate-limit, …).
    """
    from datetime import datetime as _dt

    if not account.encrypted_password:
        raise IGClientError(
            f"لا يوجد كلمة مرور مخزنة للحساب @{account.username} — "
            "يتعذر التجديد التلقائي. أعد ربط الحساب بكلمة المرور."
        )

    try:
        password = crypto.decrypt(account.encrypted_password)
    except Exception as exc:
        raise IGClientError(f"فشل فكّ تشفير كلمة المرور: {exc}") from exc

    totp_code: str | None = None
    if account.encrypted_totp_secret:
        try:
            from . import totp as _totp
            secret = crypto.decrypt(account.encrypted_totp_secret)
            totp_code = _totp.generate_code(secret)
            logger.debug("Generated TOTP code for auto-relogin of @%s", account.username)
        except Exception as exc:
            logger.warning(
                "Could not generate TOTP for @%s during auto-relogin: %s",
                account.username, exc,
            )

    proxy: str | None = None
    if account.encrypted_proxy:
        try:
            proxy = crypto.decrypt(account.encrypted_proxy)
        except Exception as exc:
            logger.warning(
                "Could not decrypt proxy for @%s during auto-relogin: %s",
                account.username, exc,
            )

    logger.info("Auto-relogin: signing in @%s …", account.username)
    cl, settings = login_with_password(
        account.username,
        password,
        verification_code=totp_code,
        proxy=proxy,
    )

    account.encrypted_session = session_to_encrypted_blob(settings)
    account.last_login_at = _dt.utcnow()
    account.session_renewed_at = _dt.utcnow()
    account.is_active = True
    account.last_error = None
    db.commit()

    logger.info("Auto-relogin successful for @%s", account.username)
    return cl
