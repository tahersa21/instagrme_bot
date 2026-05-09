"""Thin wrapper around `instagrapi` to abstract login + media fetching.

We persist the session JSON (cookies + device) encrypted in the DB so we don't
re-authenticate every run — this is safer for the account.
"""

from __future__ import annotations

import json
import logging
from typing import Any

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


def _new_client() -> Client:
    cl = Client()
    cl.delay_range = [1, 3]
    return cl


def login_with_password(
    username: str, password: str, verification_code: str | None = None
) -> tuple[Client, dict[str, Any]]:
    """Log in via username + password. Returns (client, session_settings_dict).

    Raises IG2FARequired / IGChallengeRequired / IGBadPassword on failure.
    """
    cl = _new_client()
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
    return cl, cl.get_settings()


def login_with_cookies(username: str, cookies_json: str) -> tuple[Client, dict[str, Any]]:
    """Log in by importing a previously exported session/cookies JSON.

    Accepts either:
      - a full instagrapi `settings` dict (preferred)
      - a raw browser cookies array (list of dicts)
    """
    cl = _new_client()
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
    """Rebuild a Client from the encrypted session stored on `account`."""
    if not account.encrypted_session:
        raise IGClientError(f"No saved session for account {account.username}")
    settings_dict = json.loads(crypto.decrypt(account.encrypted_session))
    cl = _new_client()
    cl.set_settings(settings_dict)
    cl.username = account.username
    return cl


def session_to_encrypted_blob(settings_dict: dict[str, Any]) -> str:
    return crypto.encrypt(json.dumps(settings_dict))
