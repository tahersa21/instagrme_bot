"""SMS provider helpers for sms-activate.org and 5sim.net.

Both providers offer the same conceptual flow:
    1) request a number for the "instagram" service
    2) poll for the SMS code
    3) mark the activation complete (or cancel)
"""

from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)


class SmsError(Exception):
    pass


# ---------------- sms-activate.org ----------------

_SA_BASE = "https://api.sms-activate.org/stubs/handler_api.php"


def _sa_get(api_key: str, params: dict) -> str:
    p = {"api_key": api_key, **params}
    r = httpx.get(_SA_BASE, params=p, timeout=20.0)
    r.raise_for_status()
    return r.text.strip()


def sa_get_number(api_key: str, country: str) -> tuple[str, str]:
    """Returns (phone_number, activation_id)."""
    resp = _sa_get(api_key, {"action": "getNumber", "service": "ig", "country": country})
    if not resp.startswith("ACCESS_NUMBER"):
        raise SmsError(f"sms-activate getNumber failed: {resp}")
    _, activation_id, phone = resp.split(":")
    return phone, activation_id


def sa_get_code(api_key: str, activation_id: str, timeout: int = 300, poll: int = 5) -> str | None:
    _sa_get(api_key, {"action": "setStatus", "status": "1", "id": activation_id})
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = _sa_get(api_key, {"action": "getStatus", "id": activation_id})
        if resp.startswith("STATUS_OK"):
            return resp.split(":", 1)[1]
        if resp == "STATUS_CANCEL":
            return None
        time.sleep(poll)
    return None


def sa_finish(api_key: str, activation_id: str, success: bool) -> None:
    status = "6" if success else "8"  # 6 = complete, 8 = cancel
    try:
        _sa_get(api_key, {"action": "setStatus", "status": status, "id": activation_id})
    except Exception:
        pass


# ---------------- 5sim.net ----------------

_5SIM_BASE = "https://5sim.net/v1"


def _5sim_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def fivesim_get_number(api_key: str, country: str) -> tuple[str, str]:
    country = country or "any"
    url = f"{_5SIM_BASE}/user/buy/activation/{country}/any/instagram"
    r = httpx.get(url, headers=_5sim_headers(api_key), timeout=20.0)
    if r.status_code != 200:
        raise SmsError(f"5sim buy failed ({r.status_code}): {r.text}")
    data = r.json()
    return data["phone"], str(data["id"])


def fivesim_get_code(
    api_key: str, activation_id: str, timeout: int = 300, poll: int = 5
) -> str | None:
    url = f"{_5SIM_BASE}/user/check/{activation_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = httpx.get(url, headers=_5sim_headers(api_key), timeout=15.0)
        if r.status_code == 200:
            data = r.json()
            sms_list = data.get("sms") or []
            if sms_list:
                return sms_list[-1].get("code")
        time.sleep(poll)
    return None


def fivesim_finish(api_key: str, activation_id: str, success: bool) -> None:
    action = "finish" if success else "cancel"
    try:
        httpx.get(
            f"{_5SIM_BASE}/user/{action}/{activation_id}",
            headers=_5sim_headers(api_key),
            timeout=15.0,
        )
    except Exception:
        pass


# ---------------- dispatch ----------------


def get_number(provider_type: str, api_key: str, country: str) -> tuple[str, str]:
    if provider_type == "sms-activate":
        return sa_get_number(api_key, country)
    if provider_type == "5sim":
        return fivesim_get_number(api_key, country)
    raise SmsError(f"Unknown provider_type: {provider_type}")


def get_code(provider_type: str, api_key: str, activation_id: str, timeout: int = 300) -> str | None:
    if provider_type == "sms-activate":
        return sa_get_code(api_key, activation_id, timeout=timeout)
    if provider_type == "5sim":
        return fivesim_get_code(api_key, activation_id, timeout=timeout)
    raise SmsError(f"Unknown provider_type: {provider_type}")


def finish(provider_type: str, api_key: str, activation_id: str, success: bool) -> None:
    if provider_type == "sms-activate":
        sa_finish(api_key, activation_id, success)
    elif provider_type == "5sim":
        fivesim_finish(api_key, activation_id, success)
