"""Core automation job — human-behaviour simulation layer.

Anti-detection techniques applied
──────────────────────────────────
1.  Gaussian timing        — delays follow a bell-curve, not a suspicious flat range.
2.  Fatigue factor         — every N actions the bot slows down, like a real person.
3.  Skip probability       — configurable per account (default ~15 %).
4.  Target shuffle         — processes targets in a different order each run.
5.  Profile visit          — views the target's profile before engaging (scrolls medias).
6.  Warm-up browsing       — feed / explore / inbox / own-profile before any action.
7.  Story watch            — per-target optional story viewing.
8.  Random comment         — per-target optional comment from a pool of templates.
9.  Proxy per account      — already applied in ig_client.restore_client().
10. Unique device          — instagrapi session stores a stable random Android fingerprint.
11. Personality profile    — skip_rate / session_style / warmup_count per account.
12. Active-hours window    — bot only runs between configured UTC hours.
13. New-account mode       — automatically halves limits for accounts < 30 days old.
14. Action-sequence noise  — story / profile visit order randomised per run.
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
from ..models import Account, LikeLog, Run, RunStatus, SettingsKV, Target
from . import ig_client

logger = logging.getLogger(__name__)


# ─── timing helpers ───────────────────────────────────────────────────────────

def _gauss_sleep(mean: float, sigma_frac: float = 0.3, mn: float = 3.0) -> None:
    """Sleep for a Gaussian-distributed duration around `mean` seconds."""
    sigma = mean * sigma_frac
    duration = max(mn, random.gauss(mean, sigma))
    logger.debug("Sleeping %.1fs", duration)
    time.sleep(duration)


def _fatigue_sleep(actions_done: int, base_mean: float) -> None:
    """Add an extra pause every 10 actions to simulate human fatigue."""
    if actions_done > 0 and actions_done % 10 == 0:
        pause = random.gauss(45, 10)
        logger.info("Fatigue pause after %d actions — %.0fs", actions_done, pause)
        time.sleep(max(20, pause))


# ─── settings helpers ─────────────────────────────────────────────────────────

def _db_setting(db: Session, key: str, default: str) -> str:
    row = db.get(SettingsKV, key)
    return row.value if row else default


def _db_flag(db: Session, key: str, default: bool = True) -> bool:
    row = db.get(SettingsKV, key)
    if row is None:
        return default
    return row.value != "false"


# ─── active-hours check ───────────────────────────────────────────────────────

def _is_within_active_hours(db: Session) -> bool:
    """Return True if the current UTC hour is within the configured active window."""
    start = int(_db_setting(db, "active_hours_start", "8"))
    end = int(_db_setting(db, "active_hours_end", "23"))
    hour = datetime.utcnow().hour
    if start <= end:
        return start <= hour <= end
    # window wraps midnight (e.g. 22 → 6)
    return hour >= start or hour <= end


# ─── personality helpers ───────────────────────────────────────────────────────

def _get_personality(account: Account) -> dict:
    """Parse per-account personality JSON, falling back to safe defaults."""
    defaults: dict = {"skip_rate": 0.15, "session_style": "moderate", "warmup_count": 3}
    if not account.personality:
        return defaults
    try:
        data = json.loads(account.personality)
        return {**defaults, **data}
    except Exception:
        return defaults


def _delay_multiplier(session_style: str) -> float:
    return {"active": 0.8, "moderate": 1.0, "quiet": 1.5}.get(session_style, 1.0)


# ─── new-account mode ─────────────────────────────────────────────────────────

def _apply_new_account_limits(
    account: Account, daily: int, hourly: int, enabled: bool
) -> tuple[int, int]:
    """Halve limits for accounts younger than 30 days when new_account_mode is on."""
    if not enabled:
        return daily, hourly
    age_days = (datetime.utcnow() - account.created_at).days
    if age_days < 30:
        logger.info(
            "New-account mode: %s is %d days old — limits halved (%d daily, %d hourly)",
            account.username, age_days, daily // 2, hourly // 2,
        )
        return max(1, daily // 2), max(1, hourly // 2)
    return daily, hourly


# ─── db helpers ───────────────────────────────────────────────────────────────

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


# ─── warm-up browsing ─────────────────────────────────────────────────────────

def _warmup_browse(client: object, count: int = 3) -> None:  # type: ignore[type-arg]
    """Simulate a short human-like browsing session before any real actions."""
    logger.info("Starting warm-up browsing (%d actions)", count)

    def _browse_timeline() -> None:
        try:
            client.get_timeline_feed()  # type: ignore[attr-defined]
            logger.info("Warm-up: scrolled timeline")
            _gauss_sleep(6, mn=4)
        except Exception as exc:
            logger.debug("Warm-up timeline skipped: %s", exc)

    def _browse_explore() -> None:
        try:
            client.explore()  # type: ignore[attr-defined]
            logger.info("Warm-up: browsed explore")
            _gauss_sleep(5, mn=3)
        except Exception as exc:
            logger.debug("Warm-up explore skipped: %s", exc)

    def _view_own_profile() -> None:
        try:
            client.account_info()  # type: ignore[attr-defined]
            logger.info("Warm-up: viewed own profile")
            _gauss_sleep(3, mn=2)
        except Exception as exc:
            logger.debug("Warm-up profile view skipped: %s", exc)

    def _check_inbox() -> None:
        try:
            client.direct_threads()  # type: ignore[attr-defined]
            logger.info("Warm-up: checked inbox")
            _gauss_sleep(3, mn=2)
        except Exception as exc:
            logger.debug("Warm-up inbox skipped: %s", exc)

    def _browse_reels() -> None:
        try:
            client.get_timeline_feed()  # type: ignore[attr-defined]
            logger.info("Warm-up: browsed reels feed")
            _gauss_sleep(4, mn=2)
        except Exception as exc:
            logger.debug("Warm-up reels skipped: %s", exc)

    actions = [
        ("timeline", _browse_timeline),
        ("explore", _browse_explore),
        ("profile", _view_own_profile),
        ("inbox", _check_inbox),
        ("reels", _browse_reels),
    ]
    random.shuffle(actions)
    chosen_count = max(1, min(count, len(actions)))
    for label, fn in actions[:chosen_count]:
        logger.info("Warm-up action: %s", label)
        fn()
        _gauss_sleep(2, mn=1)

    logger.info("Warm-up complete")


# ─── profile visit simulation ─────────────────────────────────────────────────

def _visit_profile(client: object, user_id: str | int, username: str) -> None:
    """Simulate opening and scrolling through a target's profile page."""
    try:
        client.user_info(user_id)  # type: ignore[attr-defined]
        logger.info("Visited profile of @%s", username)
        _gauss_sleep(4, mn=2)
        client.user_medias(user_id, amount=random.randint(3, 6))  # type: ignore[attr-defined]
        _gauss_sleep(5, mn=3)
    except Exception as exc:
        logger.debug("Profile visit skipped for @%s: %s", username, exc)


# ─── browse-without-liking (noise action) ─────────────────────────────────────

def _browse_noise(client: object, user_id: str | int, username: str) -> None:
    """Visit a profile and scroll without liking — adds realistic noise."""
    try:
        client.user_info(user_id)  # type: ignore[attr-defined]
        client.user_medias(user_id, amount=random.randint(2, 4))  # type: ignore[attr-defined]
        logger.info("Noise browse: scrolled @%s without liking", username)
        _gauss_sleep(random.uniform(5, 12), mn=3)
    except Exception as exc:
        logger.debug("Noise browse skipped: %s", exc)


# ─── main job ─────────────────────────────────────────────────────────────────

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
    cfg = get_settings()
    hourly_limit = hourly_limit or cfg.default_hourly_like_limit
    daily_limit = daily_limit or cfg.default_daily_like_limit
    min_delay = min_delay or cfg.default_min_delay_seconds
    max_delay = max_delay or cfg.default_max_delay_seconds

    # ── Active-hours check ─────────────────────────────────────────────────────
    if triggered_by != "manual" and not _is_within_active_hours(db):
        hour = datetime.utcnow().hour
        run = Run(
            account_id=account.id,
            status=RunStatus.STOPPED,
            triggered_by=triggered_by,
            error=f"خارج نافذة ساعات النشاط (الساعة الحالية UTC: {hour})",
        )
        run.finished_at = datetime.utcnow()
        db.add(run)
        db.commit()
        logger.info("Skipping run for @%s — outside active hours (UTC %d)", account.username, hour)
        return run

    # ── Per-account personality ────────────────────────────────────────────────
    personality = _get_personality(account)
    skip_rate: float = personality["skip_rate"]
    session_style: str = personality["session_style"]
    warmup_count: int = personality["warmup_count"]
    delay_mult = _delay_multiplier(session_style)

    delay_mean = ((min_delay + max_delay) / 2) * delay_mult

    # ── New-account mode ───────────────────────────────────────────────────────
    new_account_mode = _db_flag(db, "new_account_mode", default=True)
    daily_limit, hourly_limit = _apply_new_account_limits(
        account, daily_limit, hourly_limit, new_account_mode
    )

    run = Run(account_id=account.id, status=RunStatus.RUNNING, triggered_by=triggered_by)
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        client = ig_client.restore_client(account)
    except Exception as exc:
        logger.warning(
            "Session restore failed for @%s — attempting auto-relogin: %s",
            account.username, exc,
        )
        try:
            client = ig_client.relogin_account(account, db)
            run.error = "تم تجديد الجلسة تلقائياً (جلسة سابقة منتهية)"
            db.commit()
        except Exception as relogin_exc:
            run.status = RunStatus.FAILED
            run.finished_at = datetime.utcnow()
            run.error = f"فشل استعادة الجلسة وفشل التجديد التلقائي: {relogin_exc}"
            account.last_error = str(relogin_exc)
            db.commit()
            return run

    # ── 1. Warm-up ────────────────────────────────────────────────────────────
    if _db_flag(db, "warmup_enabled", default=True):
        try:
            _warmup_browse(client, count=warmup_count)
        except Exception as exc:
            logger.warning("Warm-up error: %s", exc)

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

    # ── 2. Shuffle targets each run ────────────────────────────────────────────
    random.shuffle(targets)

    now = datetime.utcnow()
    likes_today = _count_likes_since(db, account.id, now - timedelta(days=1))
    likes_hour = _count_likes_since(db, account.id, now - timedelta(hours=1))
    total_actions = 0

    # Guard: attempt auto-relogin at most once per run to avoid loops
    _session_refreshed_this_run: bool = False

    def _handle_login_required(exc: Exception) -> "Client | None":
        """Try auto-relogin once per run. Returns new client or None."""
        nonlocal _session_refreshed_this_run
        if _session_refreshed_this_run:
            logger.warning(
                "LoginRequired again after already relogging for @%s — giving up",
                account.username,
            )
            return None
        logger.info(
            "LoginRequired mid-run for @%s — attempting auto-relogin: %s",
            account.username, exc,
        )
        try:
            new_client = ig_client.relogin_account(account, db)
            _session_refreshed_this_run = True
            existing = run.error or ""
            run.error = (existing + " | تم تجديد الجلسة تلقائياً أثناء التشغيل").lstrip(" | ")
            db.commit()
            return new_client
        except Exception as relogin_exc:
            logger.error(
                "Auto-relogin failed for @%s: %s", account.username, relogin_exc
            )
            account.last_error = f"فشل تجديد الجلسة تلقائياً: {relogin_exc}"
            account.is_active = False
            db.commit()
            return None

    for idx, target in enumerate(targets):
        if likes_today >= daily_limit:
            logger.info("Daily limit reached (%s)", daily_limit)
            break

        # ── Occasional noise browse between every 2-3 targets ─────────────────
        if idx > 0 and idx % random.randint(2, 3) == 0:
            try:
                noise_user_id = client.user_id_from_username(target.username)
                _browse_noise(client, noise_user_id, target.username)
            except Exception:
                pass

        try:
            user_id = client.user_id_from_username(target.username)
        except LoginRequired as exc:
            new_client = _handle_login_required(exc)
            if new_client is None:
                run.status = RunStatus.FAILED
                run.finished_at = datetime.utcnow()
                run.error = (run.error or "") + f" | انتهت الجلسة ولم يتم تجديدها: {exc}"
                db.commit()
                return run
            client = new_client
            try:
                user_id = client.user_id_from_username(target.username)
            except Exception:
                run.likes_failed += 1
                db.commit()
                continue
        except (PleaseWaitFewMinutes, ClientError) as exc:
            logger.warning("Could not resolve user_id for %s: %s", target.username, exc)
            run.likes_failed += 1
            db.commit()
            continue

        # ── 3. Randomise whether stories come before or after profile visit ────
        do_stories_first = random.random() < 0.5

        if do_stories_first and target.story_watch_enabled:
            try:
                stories = client.user_stories(user_id)
                if stories:
                    client.story_seen([s.pk for s in stories])
                    logger.info("Watched %d stories for @%s", len(stories), target.username)
                    _gauss_sleep(4, mn=2)
            except Exception as exc:
                logger.warning("Story watch failed for @%s: %s", target.username, exc)

        # ── 4. Profile visit ──────────────────────────────────────────────────
        _visit_profile(client, user_id, target.username)

        if not do_stories_first and target.story_watch_enabled:
            try:
                stories = client.user_stories(user_id)
                if stories:
                    client.story_seen([s.pk for s in stories])
                    logger.info("Watched %d stories for @%s (after profile)", len(stories), target.username)
                    _gauss_sleep(3, mn=2)
            except Exception as exc:
                logger.warning("Story watch failed for @%s: %s", target.username, exc)

        # ── 5. Fetch media ────────────────────────────────────────────────────
        try:
            fetch_amount = min(target.likes_per_run + random.randint(1, 3), 20)
            medias = client.user_medias(user_id, amount=fetch_amount)
            random.shuffle(medias)
        except LoginRequired as exc:
            new_client = _handle_login_required(exc)
            if new_client is None:
                run.status = RunStatus.FAILED
                run.finished_at = datetime.utcnow()
                run.error = (run.error or "") + f" | انتهت الجلسة أثناء جلب المنشورات: {exc}"
                db.commit()
                return run
            client = new_client
            try:
                medias = client.user_medias(user_id, amount=fetch_amount)
                random.shuffle(medias)
            except Exception:
                run.likes_failed += 1
                db.commit()
                continue
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

        liked_this_target = 0

        for media in medias:
            if liked_this_target >= target.likes_per_run:
                break

            run.likes_attempted += 1

            # ── 6. Per-account skip probability ───────────────────────────────
            if random.random() < skip_rate:
                logger.debug("Randomly skipping post %s (skip_rate=%.0f%%)", media.id, skip_rate * 100)
                run.likes_skipped += 1
                db.add(LikeLog(
                    run_id=run.id, account_id=account.id,
                    target_username=target.username, media_id=str(media.id),
                    success=False, skipped_reason="random_skip",
                ))
                db.commit()
                _gauss_sleep(random.uniform(2, 5), mn=1)
                continue

            if _already_liked(db, account.id, str(media.id)):
                run.likes_skipped += 1
                db.add(LikeLog(
                    run_id=run.id, account_id=account.id,
                    target_username=target.username, media_id=str(media.id),
                    success=False, skipped_reason="already_liked",
                ))
                db.commit()
                continue

            if likes_today >= daily_limit or likes_hour >= hourly_limit:
                run.likes_skipped += 1
                db.add(LikeLog(
                    run_id=run.id, account_id=account.id,
                    target_username=target.username, media_id=str(media.id),
                    success=False, skipped_reason="rate_limit",
                ))
                db.commit()
                break

            # ── 7. Like ───────────────────────────────────────────────────────
            try:
                _gauss_sleep(random.uniform(2, 6), sigma_frac=0.2, mn=1)

                client.media_like(media.id)
                run.likes_succeeded += 1
                liked_this_target += 1
                likes_today += 1
                likes_hour += 1
                total_actions += 1

                media_url = f"https://www.instagram.com/p/{media.code}/" if media.code else None
                db.add(LikeLog(
                    run_id=run.id, account_id=account.id,
                    target_username=target.username, media_id=str(media.id),
                    media_url=media_url, success=True,
                ))
                db.commit()

                # ── 8. Comment after like ─────────────────────────────────────
                if target.comment_enabled and templates:
                    comment_text = _pick_comment(templates)
                    if comment_text:
                        try:
                            _gauss_sleep(random.uniform(4, 10), mn=3)
                            client.media_comment(media.id, comment_text)
                            logger.info("Commented on %s: %s", media.id, comment_text)
                        except Exception as exc:
                            logger.warning("Comment failed on %s: %s", media.id, exc)

            except LoginRequired as exc:
                new_client = _handle_login_required(exc)
                if new_client is None:
                    run.status = RunStatus.FAILED
                    run.finished_at = datetime.utcnow()
                    run.error = (run.error or "") + f" | انتهت الجلسة أثناء الإعجاب: {exc}"
                    db.commit()
                    return run
                client = new_client
                run.likes_failed += 1
                db.add(LikeLog(
                    run_id=run.id, account_id=account.id,
                    target_username=target.username, media_id=str(media.id),
                    success=False, error="session_expired_relogined",
                ))
                db.commit()
            except PleaseWaitFewMinutes as exc:
                run.status = RunStatus.STOPPED
                run.error = f"Rate-limited by Instagram: {exc}"
                db.commit()
                return run
            except ClientError as exc:
                run.likes_failed += 1
                db.add(LikeLog(
                    run_id=run.id, account_id=account.id,
                    target_username=target.username, media_id=str(media.id),
                    success=False, error=str(exc),
                ))
                db.commit()

            # ── 9. Gaussian delay (with session-style multiplier) ─────────────
            _gauss_sleep(delay_mean)

            # ── 10. Fatigue pause every 10 actions ────────────────────────────
            _fatigue_sleep(total_actions, delay_mean)

        # Pause between targets
        _gauss_sleep(random.uniform(5, 15) * delay_mult, mn=4)

    run.status = RunStatus.COMPLETED
    run.finished_at = datetime.utcnow()
    account.last_login_at = datetime.utcnow()
    account.last_error = None
    db.commit()
    return run
