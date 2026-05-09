from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, Target
from ..schemas.target import TargetCreate, TargetOut, TargetUpdate
from ..services.auth import get_current_user

router = APIRouter(
    prefix="/api/accounts/{account_id}/targets",
    tags=["targets"],
    dependencies=[Depends(get_current_user)],
)


def _ensure_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("", response_model=list[TargetOut])
def list_targets(account_id: int, db: Session = Depends(get_db)) -> list[Target]:
    _ensure_account(db, account_id)
    stmt = select(Target).where(Target.account_id == account_id).order_by(Target.created_at.desc())
    return list(db.scalars(stmt))


@router.post("", response_model=TargetOut, status_code=status.HTTP_201_CREATED)
def create_target(
    account_id: int, payload: TargetCreate, db: Session = Depends(get_db)
) -> Target:
    _ensure_account(db, account_id)
    target = Target(
        account_id=account_id,
        username=payload.username.lstrip("@").lower(),
        likes_per_run=payload.likes_per_run,
        is_enabled=payload.is_enabled,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.patch("/{target_id}", response_model=TargetOut)
def update_target(
    account_id: int, target_id: int, payload: TargetUpdate, db: Session = Depends(get_db)
) -> Target:
    target = db.get(Target, target_id)
    if not target or target.account_id != account_id:
        raise HTTPException(status_code=404, detail="Target not found")
    if payload.likes_per_run is not None:
        target.likes_per_run = payload.likes_per_run
    if payload.is_enabled is not None:
        target.is_enabled = payload.is_enabled
    db.commit()
    db.refresh(target)
    return target


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_target(account_id: int, target_id: int, db: Session = Depends(get_db)) -> None:
    target = db.get(Target, target_id)
    if not target or target.account_id != account_id:
        raise HTTPException(status_code=404, detail="Target not found")
    db.delete(target)
    db.commit()
