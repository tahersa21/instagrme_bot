from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, LikeLog
from ..schemas.run import LikeLogOut
from ..services.auth import get_current_user

router = APIRouter(
    prefix="/api/accounts/{account_id}/logs",
    tags=["logs"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[LikeLogOut])
def list_logs(
    account_id: int, limit: int = 100, db: Session = Depends(get_db)
) -> list[LikeLog]:
    if not db.get(Account, account_id):
        raise HTTPException(status_code=404, detail="Account not found")
    stmt = (
        select(LikeLog)
        .where(LikeLog.account_id == account_id)
        .order_by(LikeLog.created_at.desc())
        .limit(min(limit, 500))
    )
    return list(db.scalars(stmt))
