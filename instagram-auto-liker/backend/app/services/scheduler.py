"""APScheduler bootstrap — runs the auto-liker job on a configurable interval."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from ..config import get_settings
from ..database import SessionLocal
from ..models import Account, SettingsKV
from . import liker

logger = logging.getLogger(__name__)

JOB_ID = "auto-like-job"

_scheduler: BackgroundScheduler | None = None


def _get_interval_hours(default: int) -> int:
    with SessionLocal() as db:
        row = db.get(SettingsKV, "schedule_interval_hours")
        if row and row.value.isdigit():
            return int(row.value)
    return default


def _get_enabled() -> bool:
    with SessionLocal() as db:
        row = db.get(SettingsKV, "schedule_enabled")
        return bool(row and row.value == "true")


def _scheduled_run() -> None:
    """Entry point invoked by APScheduler — likes for every active account."""
    if not _get_enabled():
        logger.info("Scheduler disabled — skipping run")
        return
    with SessionLocal() as db:
        accounts = list(db.scalars(select(Account).where(Account.is_active.is_(True))))
        for account in accounts:
            try:
                liker.run_like_job(db, account, triggered_by="scheduler")
            except Exception:
                logger.exception("Scheduled run failed for account %s", account.username)


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler:
        return _scheduler

    settings = get_settings()
    interval_hours = _get_interval_hours(settings.default_schedule_interval_hours)

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _scheduled_run,
        trigger=IntervalTrigger(hours=interval_hours),
        id=JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler started — interval %sh", interval_hours)
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def reschedule(interval_hours: int) -> None:
    if _scheduler and interval_hours > 0:
        _scheduler.reschedule_job(JOB_ID, trigger=IntervalTrigger(hours=interval_hours))


def trigger_now() -> None:
    """Fire the job once, immediately, without waiting for the interval."""
    if _scheduler:
        _scheduler.add_job(_scheduled_run, id=f"{JOB_ID}-manual", replace_existing=True)
