"""Analytics & statistics endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, LikeLog
from ..services.auth import get_current_user

router = APIRouter(
    prefix="/api/stats",
    tags=["stats"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)) -> dict:
    """Return headline stats + daily breakdown for the last 7 days."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seven_days_ago = now - timedelta(days=7)

    # ── Total likes in last 7 days ────────────────────────────────────────────
    total_7d = int(
        db.scalar(
            select(func.count(LikeLog.id)).where(
                LikeLog.success.is_(True),
                LikeLog.created_at >= seven_days_ago,
            )
        )
        or 0
    )

    # ── Success rate (last 7 days, excluding already_liked / random_skip) ─────
    attempted = int(
        db.scalar(
            select(func.count(LikeLog.id)).where(
                LikeLog.created_at >= seven_days_ago,
                LikeLog.skipped_reason.is_(None),
            )
        )
        or 0
    )
    success_rate = round((total_7d / attempted * 100) if attempted else 0, 1)

    # ── Active accounts ────────────────────────────────────────────────────────
    accounts_active = int(
        db.scalar(select(func.count(Account.id)).where(Account.is_active.is_(True))) or 0
    )

    # ── Daily breakdown: likes per day for last 7 days ────────────────────────
    by_day: list[dict] = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = int(
            db.scalar(
                select(func.count(LikeLog.id)).where(
                    LikeLog.success.is_(True),
                    LikeLog.created_at >= day_start,
                    LikeLog.created_at < day_end,
                )
            )
            or 0
        )
        by_day.append({"date": day_start.strftime("%Y-%m-%d"), "likes": count})

    # ── Per-account breakdown (last 7 days) ───────────────────────────────────
    rows = db.execute(
        select(Account.username, func.count(LikeLog.id).label("likes"))
        .join(LikeLog, LikeLog.account_id == Account.id)
        .where(LikeLog.success.is_(True), LikeLog.created_at >= seven_days_ago)
        .group_by(Account.username)
        .order_by(func.count(LikeLog.id).desc())
    ).all()
    by_account = [{"username": r.username, "likes": r.likes} for r in rows]

    # ── Today's count ─────────────────────────────────────────────────────────
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_likes = int(
        db.scalar(
            select(func.count(LikeLog.id)).where(
                LikeLog.success.is_(True),
                LikeLog.created_at >= today_start,
            )
        )
        or 0
    )

    return {
        "total_7d": total_7d,
        "today_likes": today_likes,
        "success_rate": success_rate,
        "accounts_active": accounts_active,
        "by_day": by_day,
        "by_account": by_account,
    }
