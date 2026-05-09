"""Schedule settings — enable/disable, change interval, rate limits, warmup."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import SettingsKV
from ..schemas.settings import ScheduleSettingsIn, ScheduleSettingsOut
from ..services import scheduler
from ..services.auth import get_current_user

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)],
)

KEYS = (
    "schedule_enabled",
    "schedule_interval_hours",
    "daily_like_limit",
    "hourly_like_limit",
    "min_delay_seconds",
    "max_delay_seconds",
    "warmup_enabled",
)


def _get(db: Session, key: str) -> str | None:
    row = db.get(SettingsKV, key)
    return row.value if row else None


def _set(db: Session, key: str, value: str) -> None:
    row = db.get(SettingsKV, key)
    if row:
        row.value = value
    else:
        db.add(SettingsKV(key=key, value=value))


@router.get("/schedule", response_model=ScheduleSettingsOut)
def get_schedule(db: Session = Depends(get_db)) -> ScheduleSettingsOut:
    s = get_settings()
    warmup_raw = _get(db, "warmup_enabled")
    return ScheduleSettingsOut(
        enabled=_get(db, "schedule_enabled") == "true",
        interval_hours=int(
            _get(db, "schedule_interval_hours") or s.default_schedule_interval_hours
        ),
        daily_like_limit=int(_get(db, "daily_like_limit") or s.default_daily_like_limit),
        hourly_like_limit=int(_get(db, "hourly_like_limit") or s.default_hourly_like_limit),
        min_delay_seconds=int(_get(db, "min_delay_seconds") or s.default_min_delay_seconds),
        max_delay_seconds=int(_get(db, "max_delay_seconds") or s.default_max_delay_seconds),
        warmup_enabled=warmup_raw != "false",
    )


@router.put("/schedule", response_model=ScheduleSettingsOut)
def update_schedule(
    payload: ScheduleSettingsIn, db: Session = Depends(get_db)
) -> ScheduleSettingsOut:
    _set(db, "schedule_enabled", "true" if payload.enabled else "false")
    _set(db, "schedule_interval_hours", str(payload.interval_hours))
    _set(db, "daily_like_limit", str(payload.daily_like_limit))
    _set(db, "hourly_like_limit", str(payload.hourly_like_limit))
    _set(db, "min_delay_seconds", str(payload.min_delay_seconds))
    _set(db, "max_delay_seconds", str(payload.max_delay_seconds))
    _set(db, "warmup_enabled", "true" if payload.warmup_enabled else "false")
    db.commit()

    scheduler.reschedule(payload.interval_hours)

    return ScheduleSettingsOut(**payload.model_dump())


@router.post("/schedule/run-now", response_model=dict)
def run_now() -> dict:
    scheduler.trigger_now()
    return {"status": "triggered"}
