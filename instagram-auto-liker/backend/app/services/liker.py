"""Core automation job: likes, comments, and story views.

Iterates target accounts, likes their latest media, optionally leaves a
comment, and optionally marks their stories as seen — all within the
configured rate limits.
"""

from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime, timedelta

from instagrapi.exceptions import ClientError, LoginRequired, PleaseWaitFewMinutes
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Account, LikeLog, Run, RunStatus, Target
from . import ig_client

logger = logging.getLogger(__name__)


def _count_likes_since(db: Session, account_id: int, since: datetime) -> int:
    stmt = select(func.count(LikeLog.id)).where(
        LikeLog.account_id == account_id,
        LikeLog.success.is_(True),
        LikeLog.created_at >= since,
    )
    return int(db.scalar(stmt) or 0)


def _already_liked(db: Session, account_id: int, media_id: str) -> bool:
    stmt = select(func.count(LikeLog.id)).where(
        LikeLog.account_id == account_id,
        LikeLog.media_id == media_id,
        LikeLog.success.is_(True),
    )
    return (db.scalar(stmt) or 0) > 0


def _pick_comment(templates: list[str]) -> str | None:
    clean = [t.strip() for t in templates if t.strip()]
    return random.choice(clean) if clean else None


def run_like_job(
    db: Session,
    account: Account,
    triggered_by: str = "manual",
    hourly_limit: int | None = None,
    daily_limit: int | None = None,
    min_delay: int | None = None,
    max_delay: int | None = None,
) -> Run:
    """Execute one automation pass for the given account. Returns the persisted Run."""
    settings = get_settings()
    hourly_limit = hourly_limit or settings.default_hourly_like_limit
    daily_limit = daily_limit or settings.default_daily_like_limit
    min_delay = min_delay or settings.default_min_delay_seconds
    max_delay = max_delay or settings.default_max_delay_seconds

    run = Run(account_id=account.id, status=RunStatus.RUNNING, triggered_by=triggered_by)
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        client = ig_client.restore_client(account)
    except Exception as exc:
        run.status = RunStatus.FAILED
        run.finished_at = datetime.utcnow()
        run.error = f"Failed to restore session: {exc}"
        account.last_error = str(exc)
        db.commit()
        return run

    targets = list(
        db.scalars(
            select(Target).where(Target.account_id == account.id, Target.is_enabled.is_(True))
        )
    )
    if not targets:
        run.status = RunStatus.COMPLETED
        run.finished_at = datetime.utcnow()
        run.error = "No enabled targets configured"
        db.commit()
        return run

    now = datetime.utcnow()
    likes_today = _count_likes_since(db, account.id, now - timedelta(days=1))
    likes_hour = _count_likes_since(db, account.id, now - timedelta(hours=1))

    for target in targets:
        if likes_today >= daily_limit:
            logger.info("Daily like limit reached (%s); stopping run", daily_limit)
            break

        try:
            user_id = client.user_id_from_username(target.username)
        except (LoginRequired, PleaseWaitFewMinutes, ClientError) as exc:
            logger.warning("Could not resolve user_id for %s: %s", target.username, exc)
            run.likes_failed += 1
            db.commit()
            continue

        # ── Stories ──────────────────────────────────────────────────────────
        if target.story_watch_enabled:
            try:
                stories = client.user_stories(user_id)
                if stories:
                    client.story_seen([s.pk for s in stories])
                    logger.info("Watched %d stories for @%s", len(stories), target.username)
                    time.sleep(random.uniform(2, 5))
            except Exception as exc:
                logger.warning("Story watch failed for @%s: %s", target.username, exc)

        # ── Likes (+ optional comments) ───────────────────────────────────
        try:
            medias = client.user_medias(user_id, amount=target.likes_per_run)
        except LoginRequired as exc:
            run.status = RunStatus.FAILED
            run.error = f"Login required mid-run: {exc}"
            account.last_error = str(exc)
            account.is_active = False
            db.commit()
            return run
        except PleaseWaitFewMinutes as exc:
            run.status = RunStatus.STOPPED
            run.error = f"Rate-limited by Instagram: {exc}"
            db.commit()
            return run
        except ClientError as exc:
            logger.warning("Failed to fetch media for %s: %s", target.username, exc)
            run.likes_failed += 1
            db.commit()
            continue

        templates: list[str] = []
        if target.comment_enabled:
            try:
                templates = json.loads(target.comment_templates or "[]")
            except Exception:
                templates = []

        for media in medias:
            run.likes_attempted += 1

            if _already_liked(db, account.id, str(media.id)):
                run.likes_skipped += 1
                db.add(
                    LikeLog(
                        run_id=run.id,
                        account_id=account.id,
                        target_username=target.username,
                        media_id=str(media.id),
                        success=False,
                        skipped_reason="already_liked",
                    )
                )
                db.commit()
                continue

            if likes_today >= daily_limit or likes_hour >= hourly_limit:
                run.likes_skipped += 1
                db.add(
                    LikeLog(
                        run_id=run.id,
                        account_id=account.id,
                        target_username=target.username,
                        media_id=str(media.id),
                        success=False,
                        skipped_reason="rate_limit",
                    )
                )
                db.commit()
                break

            try:
                client.media_like(media.id)
                run.likes_succeeded += 1
                likes_today += 1
                likes_hour += 1
                media_url = f"https://www.instagram.com/p/{media.code}/" if media.code else None
                db.add(
                    LikeLog(
                        run_id=run.id,
                        account_id=account.id,
                        target_username=target.username,
                        media_id=str(media.id),
                        media_url=media_url,
                        success=True,
                    )
                )
                db.commit()

                # ── Comment after successful like ─────────────────────────
                if target.comment_enabled and templates:
                    comment_text = _pick_comment(templates)
                    if comment_text:
                        try:
                            time.sleep(random.uniform(3, 8))
                            client.media_comment(media.id, comment_text)
                            logger.info(
                                "Commented on %s for @%s: %s",
                                media.id, target.username, comment_text,
                            )
                        except Exception as exc:
                            logger.warning("Comment failed on %s: %s", media.id, exc)

            except PleaseWaitFewMinutes as exc:
                run.status = RunStatus.STOPPED
                run.error = f"Rate-limited by Instagram: {exc}"
                db.commit()
                return run
            except ClientError as exc:
                run.likes_failed += 1
                db.add(
                    LikeLog(
                        run_id=run.id,
                        account_id=account.id,
                        target_username=target.username,
                        media_id=str(media.id),
                        success=False,
                        error=str(exc),
                    )
                )
                db.commit()

            sleep_for = random.uniform(min_delay, max_delay)
            logger.info("Sleeping %.1fs after action", sleep_for)
            time.sleep(sleep_for)

    run.status = RunStatus.COMPLETED
    run.finished_at = datetime.utcnow()
    account.last_login_at = datetime.utcnow()
    account.last_error = None
    db.commit()
    return run
