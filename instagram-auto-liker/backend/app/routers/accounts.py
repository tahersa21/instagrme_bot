"""Manage Instagram accounts: login (password / cookies / playwright), proxy, personality, TOTP, list, delete."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account
from ..schemas.account import (
    AccountOut,
    IGLoginCookiesRequest,
    IGLoginPasswordRequest,
    IGLoginPlaywrightRequest,
    IGLoginResponse,
    PersonalityUpdateRequest,
    ProxyUpdateRequest,
    TOTPUpdateRequest,
)
from ..services import ig_client
from ..services import pw_login as _pw_login
from ..services import totp as _totp
from ..services.auth import get_current_user
from ..services.crypto import decrypt, encrypt

router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"],
    dependencies=[Depends(get_current_user)],
)

_VALID_PROXY_TYPES = {"residential", "mobile_4g", "datacenter"}


def _upsert_account(
    db: Session,
    username: str,
    encrypted_session: str,
    encrypted_password: str | None = None,
    encrypted_proxy: str | None = ...,  # type: ignore[assignment]
    proxy_type: str | None = ...,  # type: ignore[assignment]
    encrypted_totp_secret: str | None = ...,  # type: ignore[assignment]
) -> Account:
    account = db.scalar(select(Account).where(Account.username == username))
    if account is None:
        account = Account(username=username)
        db.add(account)
    account.encrypted_session = encrypted_session
    if encrypted_password is not None:
        account.encrypted_password = encrypted_password
    if encrypted_proxy is not ...:
        account.encrypted_proxy = encrypted_proxy
    if proxy_type is not ...:
        account.proxy_type = proxy_type
    if encrypted_totp_secret is not ...:
        account.encrypted_totp_secret = encrypted_totp_secret
    account.is_active = True
    account.last_login_at = datetime.utcnow()
    account.last_error = None
    db.commit()
    db.refresh(account)
    return account


def _to_out(account: Account) -> AccountOut:
    out = AccountOut.model_validate(account)
    out.has_proxy = bool(account.encrypted_proxy)
    out.has_totp = bool(account.encrypted_totp_secret)
    return out


def _resolve_verification_code(
    totp_secret: str | None,
    verification_code: str | None,
) -> str | None:
    """If a TOTP secret is provided, auto-generate the 6-digit code.
    Falls back to the manually supplied verification_code if no secret given.
    """
    if totp_secret:
        try:
            return _totp.generate_code(totp_secret)
        except _totp.TOTPError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return verification_code


class _TOTPPreviewRequest(BaseModel):
    totp_secret: str


class _TOTPPreviewResponse(BaseModel):
    code: str
    remaining_seconds: int


@router.post("/totp/preview", response_model=_TOTPPreviewResponse)
def preview_totp(payload: _TOTPPreviewRequest) -> _TOTPPreviewResponse:
    """Generate the current TOTP code for a given secret (for live UI preview)."""
    try:
        code = _totp.generate_code(payload.totp_secret)
        remaining = _totp.time_remaining()
    except _totp.TOTPError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _TOTPPreviewResponse(code=code, remaining_seconds=remaining)


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)) -> list[AccountOut]:
    accounts = list(db.scalars(select(Account).order_by(Account.created_at.desc())))
    return [_to_out(a) for a in accounts]


@router.post("/login/password", response_model=IGLoginResponse)
def login_password(
    payload: IGLoginPasswordRequest, db: Session = Depends(get_db)
) -> IGLoginResponse:
    proxy = payload.proxy or None
    verification_code = _resolve_verification_code(payload.totp_secret, payload.verification_code)
    try:
        _, settings_dict = ig_client.login_with_password(
            payload.username, payload.password, verification_code, proxy=proxy
        )
    except ig_client.IG2FARequired:
        return IGLoginResponse(
            account=AccountOut(
                id=0,
                username=payload.username,
                is_active=False,
                created_at=datetime.utcnow(),
            ),
            requires_2fa=True,
            message="Two-factor code required. Resubmit with verification_code.",
        )
    except ig_client.IGChallengeRequired as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ig_client.IGBadPassword as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ig_client.IGRateLimited as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except ig_client.IGClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    ptype = payload.proxy_type if payload.proxy_type in _VALID_PROXY_TYPES else None
    enc_totp = encrypt(_totp.validate_secret(payload.totp_secret)) if payload.totp_secret else None
    account = _upsert_account(
        db,
        payload.username,
        ig_client.session_to_encrypted_blob(settings_dict),
        encrypted_password=encrypt(payload.password),
        encrypted_proxy=encrypt(proxy) if proxy else None,
        proxy_type=ptype,
        encrypted_totp_secret=enc_totp,
    )
    return IGLoginResponse(account=_to_out(account))


@router.post("/login/cookies", response_model=IGLoginResponse)
def login_cookies(
    payload: IGLoginCookiesRequest, db: Session = Depends(get_db)
) -> IGLoginResponse:
    proxy = payload.proxy or None
    try:
        _, settings_dict = ig_client.login_with_cookies(
            payload.username, payload.cookies_json, proxy=proxy
        )
    except ig_client.IGClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    ptype = payload.proxy_type if payload.proxy_type in _VALID_PROXY_TYPES else None
    account = _upsert_account(
        db,
        payload.username,
        ig_client.session_to_encrypted_blob(settings_dict),
        encrypted_proxy=encrypt(proxy) if proxy else None,
        proxy_type=ptype,
    )
    return IGLoginResponse(account=_to_out(account))


@router.post("/login/playwright", response_model=IGLoginResponse)
def login_playwright(
    payload: IGLoginPlaywrightRequest, db: Session = Depends(get_db)
) -> IGLoginResponse:
    """Log in using a real headless Chromium browser via Playwright.

    If totp_secret is provided, the 6-digit code is generated automatically
    from it — no manual entry needed.
    """
    proxy = payload.proxy or None
    verification_code = _resolve_verification_code(payload.totp_secret, payload.verification_code)
    try:
        result = _pw_login.login_with_playwright(
            username=payload.username,
            password=payload.password,
            proxy=proxy,
            verification_code=verification_code,
        )
    except _pw_login.PW2FARequired:
        return IGLoginResponse(
            account=AccountOut(
                id=0,
                username=payload.username,
                is_active=False,
                created_at=datetime.utcnow(),
            ),
            requires_2fa=True,
            message="Two-factor code required. Resubmit with verification_code.",
        )
    except _pw_login.PWChallengeRequired as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except _pw_login.PWLoginError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        _, settings_dict = ig_client.login_with_playwright_session(
            payload.username, result["cookies"], proxy=proxy
        )
    except ig_client.IGClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    ptype = payload.proxy_type if payload.proxy_type in _VALID_PROXY_TYPES else None
    enc_totp = encrypt(_totp.validate_secret(payload.totp_secret)) if payload.totp_secret else None
    account = _upsert_account(
        db,
        payload.username,
        ig_client.session_to_encrypted_blob(settings_dict),
        encrypted_password=encrypt(payload.password),
        encrypted_proxy=encrypt(proxy) if proxy else None,
        proxy_type=ptype,
        encrypted_totp_secret=enc_totp,
    )
    return IGLoginResponse(account=_to_out(account))


@router.patch("/{account_id}/totp", response_model=AccountOut)
def update_totp(
    account_id: int, payload: TOTPUpdateRequest, db: Session = Depends(get_db)
) -> AccountOut:
    """Set or remove the TOTP secret for an existing account.

    Send ``totp_secret: null`` to disable automatic 2FA code generation.
    """
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if payload.totp_secret:
        try:
            clean = _totp.validate_secret(payload.totp_secret)
        except _totp.TOTPError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        account.encrypted_totp_secret = encrypt(clean)
    else:
        account.encrypted_totp_secret = None

    db.commit()
    db.refresh(account)
    return _to_out(account)


@router.patch("/{account_id}/proxy", response_model=AccountOut)
def update_proxy(
    account_id: int, payload: ProxyUpdateRequest, db: Session = Depends(get_db)
) -> AccountOut:
    """Set or clear the proxy for an existing account."""
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if payload.proxy:
        if not (
            payload.proxy.startswith("http://")
            or payload.proxy.startswith("https://")
            or payload.proxy.startswith("socks5://")
            or payload.proxy.startswith("socks4://")
        ):
            raise HTTPException(
                status_code=400,
                detail="صيغة البروكسي غير صحيحة. استخدم: http://user:pass@host:port أو socks5://host:port",
            )
        account.encrypted_proxy = encrypt(payload.proxy)
    else:
        account.encrypted_proxy = None

    if payload.proxy_type in _VALID_PROXY_TYPES:
        account.proxy_type = payload.proxy_type
    elif not payload.proxy:
        account.proxy_type = None

    db.commit()
    db.refresh(account)
    return _to_out(account)


@router.patch("/{account_id}/personality", response_model=AccountOut)
def update_personality(
    account_id: int, payload: PersonalityUpdateRequest, db: Session = Depends(get_db)
) -> AccountOut:
    """Update the per-account behaviour personality profile."""
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.personality = json.dumps({
        "skip_rate": payload.skip_rate,
        "session_style": payload.session_style,
        "warmup_count": payload.warmup_count,
    })
    db.commit()
    db.refresh(account)
    return _to_out(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)) -> None:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()
