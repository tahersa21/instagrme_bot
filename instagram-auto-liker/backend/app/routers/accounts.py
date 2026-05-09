"""Manage Instagram accounts: login (password / cookies), list, delete."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account
from ..schemas.account import (
    AccountOut,
    IGLoginCookiesRequest,
    IGLoginPasswordRequest,
    IGLoginResponse,
)
from ..services import ig_client
from ..services.auth import get_current_user
from ..services.crypto import encrypt

router = APIRouter(
    prefix="/api/accounts",
    tags=["accounts"],
    dependencies=[Depends(get_current_user)],
)


def _upsert_account(
    db: Session,
    username: str,
    encrypted_session: str,
    encrypted_password: str | None = None,
) -> Account:
    account = db.scalar(select(Account).where(Account.username == username))
    if account is None:
        account = Account(username=username)
        db.add(account)
    account.encrypted_session = encrypted_session
    if encrypted_password is not None:
        account.encrypted_password = encrypted_password
    account.is_active = True
    account.last_login_at = datetime.utcnow()
    account.last_error = None
    db.commit()
    db.refresh(account)
    return account


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.created_at.desc())))


@router.post("/login/password", response_model=IGLoginResponse)
def login_password(
    payload: IGLoginPasswordRequest, db: Session = Depends(get_db)
) -> IGLoginResponse:
    try:
        _, settings_dict = ig_client.login_with_password(
            payload.username, payload.password, payload.verification_code
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

    account = _upsert_account(
        db,
        payload.username,
        ig_client.session_to_encrypted_blob(settings_dict),
        encrypted_password=encrypt(payload.password),
    )
    return IGLoginResponse(account=AccountOut.model_validate(account))


@router.post("/login/cookies", response_model=IGLoginResponse)
def login_cookies(
    payload: IGLoginCookiesRequest, db: Session = Depends(get_db)
) -> IGLoginResponse:
    try:
        _, settings_dict = ig_client.login_with_cookies(payload.username, payload.cookies_json)
    except ig_client.IGClientError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    account = _upsert_account(
        db, payload.username, ig_client.session_to_encrypted_blob(settings_dict)
    )
    return IGLoginResponse(account=AccountOut.model_validate(account))


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)) -> None:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()
