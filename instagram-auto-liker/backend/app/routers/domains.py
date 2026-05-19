"""CRUD for email-receiving domains (Mailgun-managed)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Domain
from ..schemas.domain import DomainCreate, DomainOut, DomainUpdate
from ..services.auth import get_current_user
from ..services.crypto import encrypt

router = APIRouter(
    prefix="/api/domains",
    tags=["domains"],
    dependencies=[Depends(get_current_user)],
)


def _to_out(d: Domain) -> DomainOut:
    return DomainOut(
        id=d.id,
        name=d.name,
        mailgun_domain=d.mailgun_domain,
        is_default=d.is_default,
        notes=d.notes,
        has_api_key=bool(d.encrypted_mailgun_api_key),
        created_at=d.created_at,
    )


@router.get("", response_model=list[DomainOut])
def list_domains(db: Session = Depends(get_db)) -> list[DomainOut]:
    rows = db.scalars(select(Domain).order_by(Domain.created_at.desc())).all()
    return [_to_out(d) for d in rows]


@router.post("", response_model=DomainOut, status_code=status.HTTP_201_CREATED)
def create_domain(payload: DomainCreate, db: Session = Depends(get_db)) -> DomainOut:
    if db.scalar(select(Domain).where(Domain.name == payload.name)):
        raise HTTPException(status_code=409, detail="Domain already exists")
    d = Domain(
        name=payload.name,
        mailgun_domain=payload.mailgun_domain,
        encrypted_mailgun_api_key=encrypt(payload.mailgun_api_key),
        is_default=payload.is_default,
        notes=payload.notes,
    )
    if payload.is_default:
        db.execute(update(Domain).values(is_default=False))
    db.add(d)
    db.commit()
    db.refresh(d)
    return _to_out(d)


@router.patch("/{domain_id}", response_model=DomainOut)
def update_domain(
    domain_id: int, payload: DomainUpdate, db: Session = Depends(get_db)
) -> DomainOut:
    d = db.scalar(select(Domain).where(Domain.id == domain_id))
    if not d:
        raise HTTPException(status_code=404, detail="Domain not found")
    if payload.name is not None:
        d.name = payload.name
    if payload.mailgun_domain is not None:
        d.mailgun_domain = payload.mailgun_domain
    if payload.mailgun_api_key is not None:
        d.encrypted_mailgun_api_key = encrypt(payload.mailgun_api_key)
    if payload.notes is not None:
        d.notes = payload.notes
    if payload.is_default is True:
        db.execute(update(Domain).values(is_default=False))
        d.is_default = True
    elif payload.is_default is False:
        d.is_default = False
    db.commit()
    db.refresh(d)
    return _to_out(d)


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(domain_id: int, db: Session = Depends(get_db)) -> None:
    d = db.scalar(select(Domain).where(Domain.id == domain_id))
    if not d:
        raise HTTPException(status_code=404, detail="Domain not found")
    db.delete(d)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: domain is referenced by existing account-creation jobs.",
        )
