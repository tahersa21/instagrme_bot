"""Mailgun helper: poll a Mailgun-managed mailbox for an Instagram OTP email.

Uses the Mailgun Events API to find recent inbound messages addressed to a
specific recipient, then fetches the message body and extracts a 6-digit code.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_API_BASE = "https://api.mailgun.net/v3"
_OTP_RE = re.compile(r"\b(\d{6})\b")


def _auth(api_key: str) -> tuple[str, str]:
    return ("api", api_key)


def fetch_recent_events(
    mailgun_domain: str,
    api_key: str,
    recipient: str,
    begin_ts: float,
) -> list[dict[str, Any]]:
    """Fetch 'stored' events delivered to `recipient` since `begin_ts` (unix seconds)."""
    url = f"{_API_BASE}/{mailgun_domain}/events"
    params = {
        "event": "stored",
        "recipient": recipient,
        "begin": str(begin_ts),
        "ascending": "yes",
        "limit": 50,
    }
    try:
        r = httpx.get(url, params=params, auth=_auth(api_key), timeout=15.0)
        r.raise_for_status()
        return r.json().get("items", [])
    except Exception as exc:
        logger.warning("[mailgun] events fetch failed: %s", exc)
        return []


def fetch_message_body(storage_url: str, api_key: str) -> str:
    """Fetch the full message body (text or html) from a Mailgun storage URL."""
    try:
        r = httpx.get(storage_url, auth=_auth(api_key), timeout=15.0)
        r.raise_for_status()
        msg = r.json()
        return (msg.get("body-plain") or msg.get("stripped-text") or msg.get("body-html") or "")
    except Exception as exc:
        logger.warning("[mailgun] message fetch failed: %s", exc)
        return ""


def extract_otp(text: str) -> str | None:
    """Extract a 6-digit OTP from email text. Picks the first sequence of digits."""
    if not text:
        return None
    m = _OTP_RE.search(text)
    return m.group(1) if m else None


def wait_for_otp(
    mailgun_domain: str,
    api_key: str,
    recipient: str,
    timeout_seconds: int = 180,
    poll_interval: int = 5,
) -> str | None:
    """Block (up to `timeout_seconds`) until an OTP arrives for `recipient`."""
    begin = time.time() - 30  # small window before the request was sent
    deadline = time.time() + timeout_seconds
    seen_urls: set[str] = set()

    while time.time() < deadline:
        events = fetch_recent_events(mailgun_domain, api_key, recipient, begin)
        for ev in events:
            storage = ev.get("storage", {})
            url = storage.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            body = fetch_message_body(url, api_key)
            otp = extract_otp(body)
            if otp:
                logger.info("[mailgun] OTP received for %s", recipient)
                return otp
        time.sleep(poll_interval)

    logger.warning("[mailgun] OTP timeout for %s", recipient)
    return None
