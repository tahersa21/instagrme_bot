"""Manual run trigger + history."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..models import Account, Run
from ..schemas.run import RunOut
from ..services import liker
from ..services.auth import get_current_user

router = APIRouter(
    prefix="/api/accounts/{account_id}/runs",
    tags=["runs"],
    dependencies=[Depends(get_current_user)],
)


def _run_in_background(account_id: int) -> None:
    with SessionLocal() as db:
        account = db.get(Account, account_id)
        if not account:
            return
        liker.run_like_job(db, account, triggered_by="manual")


@router.post("", response_model=dict)
def trigger_run(
    account_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    background_tasks.add_task(_run_in_background, account_id)
    return {"status": "started", "account_id": account_id}


@router.get("", response_model=list[RunOut])
def list_runs(
    account_id: int, limit: int = 50, db: Session = Depends(get_db)
) -> list[Run]:
    if not db.get(Account, account_id):
        raise HTTPException(status_code=404, detail="Account not found")
    stmt = (
        select(Run)
        .where(Run.account_id == account_id)
        .order_by(Run.started_at.desc())
        .limit(min(limit, 200))
    )
    return list(db.scalars(stmt))
