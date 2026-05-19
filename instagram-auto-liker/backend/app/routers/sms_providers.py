"""CRUD for SMS verification providers (5sim / sms-activate)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SmsProvider
from ..schemas.sms_provider import (
    VALID_PROVIDER_TYPES,
    SmsProviderCreate,
    SmsProviderOut,
    SmsProviderUpdate,
)
from ..services.auth import get_current_user
from ..services.crypto import encrypt

router = APIRouter(
    prefix="/api/sms-providers",
    tags=["sms-providers"],
    dependencies=[Depends(get_current_user)],
)


def _to_out(s: SmsProvider) -> SmsProviderOut:
    return SmsProviderOut(
        id=s.id,
        name=s.name,
        provider_type=s.provider_type,
        country_code=s.country_code,
        is_default=s.is_default,
        has_api_key=bool(s.encrypted_api_key),
        created_at=s.created_at,
    )


@router.get("", response_model=list[SmsProviderOut])
def list_providers(db: Session = Depends(get_db)) -> list[SmsProviderOut]:
    rows = db.scalars(select(SmsProvider).order_by(SmsProvider.created_at.desc())).all()
    return [_to_out(s) for s in rows]


@router.post("", response_model=SmsProviderOut, status_code=status.HTTP_201_CREATED)
def create_provider(payload: SmsProviderCreate, db: Session = Depends(get_db)) -> SmsProviderOut:
    if payload.provider_type not in VALID_PROVIDER_TYPES:
        raise HTTPException(status_code=400, detail=f"provider_type must be one of {VALID_PROVIDER_TYPES}")
    s = SmsProvider(
        name=payload.name,
        provider_type=payload.provider_type,
        encrypted_api_key=encrypt(payload.api_key),
        country_code=payload.country_code or "0",
        is_default=payload.is_default,
    )
    if payload.is_default:
        db.execute(update(SmsProvider).values(is_default=False))
    db.add(s)
    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.patch("/{provider_id}", response_model=SmsProviderOut)
def update_provider(
    provider_id: int, payload: SmsProviderUpdate, db: Session = Depends(get_db)
) -> SmsProviderOut:
    s = db.scalar(select(SmsProvider).where(SmsProvider.id == provider_id))
    if not s:
        raise HTTPException(status_code=404, detail="Provider not found")
    if payload.name is not None:
        s.name = payload.name
    if payload.provider_type is not None:
        if payload.provider_type not in VALID_PROVIDER_TYPES:
            raise HTTPException(status_code=400, detail="Invalid provider_type")
        s.provider_type = payload.provider_type
    if payload.api_key is not None:
        s.encrypted_api_key = encrypt(payload.api_key)
    if payload.country_code is not None:
        s.country_code = payload.country_code
    if payload.is_default is True:
        db.execute(update(SmsProvider).values(is_default=False))
        s.is_default = True
    elif payload.is_default is False:
        s.is_default = False
    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: int, db: Session = Depends(get_db)) -> None:
    s = db.scalar(select(SmsProvider).where(SmsProvider.id == provider_id))
    if not s:
        raise HTTPException(status_code=404, detail="Provider not found")
    db.delete(s)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: provider is referenced by existing account-creation jobs.",
        )
