"""Instagram account creation via Playwright + Mailgun OTP + SMS provider.

WARNING: Automated account creation violates Instagram's Terms of Service and
success rates are low due to CAPTCHA, IP reputation, and behavioural detection.
This module is provided for personal/educational use only.
"""

from __future__ import annotations

import json
import logging
import random
import secrets
import string
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Account, AccountCreationJob, Domain, SmsProvider
from . import mailgun, sms_provider as sms_svc
from .crypto import decrypt, encrypt

logger = logging.getLogger(__name__)

_FIRST_NAMES = [
    "Ahmed", "Sara", "Mohamed", "Layla", "Omar", "Nour", "Yasmin", "Karim",
    "Lina", "Tariq", "Hadi", "Rana", "Sami", "Hana", "Adam", "Mira",
]
_LAST_NAMES = [
    "Hassan", "Ali", "Saleh", "Farouk", "Mansour", "Khalil", "Habib",
    "Nasser", "Rashid", "Sabri", "Younis", "Zaki", "Awad", "Badawi",
]


def _gen_username() -> str:
    return random.choice(_FIRST_NAMES).lower() + "_" + "".join(
        random.choices(string.ascii_lowercase + string.digits, k=6)
    )


def _gen_full_name() -> str:
    return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"


def _gen_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(14))


def _gen_email_local() -> str:
    return "ig" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))


def _append_log(job: AccountCreationJob, message: str) -> None:
    try:
        existing = json.loads(job.logs or "[]")
    except Exception:
        existing = []
    existing.append({"ts": datetime.utcnow().isoformat(), "msg": message})
    job.logs = json.dumps(existing)


def _set_status(db: Session, job: AccountCreationJob, status: str, error: str | None = None) -> None:
    job.status = status
    if error is not None:
        job.error = error
    if status in {"success", "failed"}:
        job.finished_at = datetime.utcnow()
    db.commit()


def prepare_job_fields(
    domain: Domain,
    full_name: str | None,
    username: str | None,
    email_local_part: str | None,
    password: str | None,
) -> dict[str, str]:
    """Generate any missing fields and return the resolved values."""
    return {
        "full_name": full_name or _gen_full_name(),
        "username": username or _gen_username(),
        "email": f"{(email_local_part or _gen_email_local()).strip()}@{domain.name}",
        "password": password or _gen_password(),
    }


def run_account_creation(job_id: int) -> None:
    """Background entrypoint: orchestrates the full account-creation flow.

    Runs in a background thread (FastAPI BackgroundTasks). Uses its own DB
    session to avoid cross-thread issues.
    """
    db = SessionLocal()
    try:
        job = db.scalar(select(AccountCreationJob).where(AccountCreationJob.id == job_id))
        if not job:
            logger.error("[account_creator] job %s not found", job_id)
            return

        job.started_at = datetime.utcnow()
        _set_status(db, job, "running")
        _append_log(job, "Started account creation workflow")
        db.commit()

        domain = db.scalar(select(Domain).where(Domain.id == job.domain_id))
        if not domain:
            _append_log(job, "Domain not found")
            _set_status(db, job, "failed", "Domain not found")
            return

        try:
            mailgun_api_key = decrypt(domain.encrypted_mailgun_api_key)
        except Exception as exc:
            _set_status(db, job, "failed", f"Failed to decrypt Mailgun API key: {exc}")
            return

        sms_p: SmsProvider | None = None
        sms_api_key: str | None = None
        if job.sms_provider_id:
            sms_p = db.scalar(select(SmsProvider).where(SmsProvider.id == job.sms_provider_id))
            if sms_p:
                try:
                    sms_api_key = decrypt(sms_p.encrypted_api_key)
                except Exception as exc:
                    _set_status(db, job, "failed", f"Failed to decrypt SMS key: {exc}")
                    return

        try:
            password = decrypt(job.encrypted_password)
        except Exception as exc:
            _set_status(db, job, "failed", f"Failed to decrypt password: {exc}")
            return

        proxy: str | None = None
        if job.encrypted_proxy:
            try:
                proxy = decrypt(job.encrypted_proxy)
            except Exception:
                proxy = None

        _append_log(job, f"Email: {job.email}")
        _append_log(job, f"Username: {job.username}")
        db.commit()

        # Attempt signup via Playwright
        try:
            from .ig_signup import perform_signup
        except Exception as exc:
            _set_status(db, job, "failed", f"Signup module unavailable: {exc}")
            return

        try:
            result = perform_signup(
                email=job.email,
                full_name=job.full_name,
                username=job.username,
                password=password,
                proxy=proxy,
                mailgun_domain=domain.mailgun_domain,
                mailgun_api_key=mailgun_api_key,
                sms_provider_type=(sms_p.provider_type if sms_p else None),
                sms_api_key=sms_api_key,
                sms_country=(sms_p.country_code if sms_p else "0"),
                on_log=lambda m: (_append_log(job, m), db.commit()),
                on_phone_assigned=lambda p: _set_phone(db, job, p),
            )
        except Exception as exc:
            logger.exception("[account_creator] signup crashed")
            _set_status(db, job, "failed", f"Signup crashed: {exc}")
            return

        if not result.get("success"):
            _set_status(db, job, "failed", result.get("error") or "Unknown signup failure")
            return

        # Persist as a real Account row
        try:
            account = Account(
                username=job.username,
                encrypted_session=encrypt(json.dumps(result.get("session") or {})),
                encrypted_password=encrypt(password),
                last_login_at=datetime.utcnow(),
            )
            if proxy:
                account.encrypted_proxy = encrypt(proxy)
            db.add(account)
            db.flush()
            job.created_account_id = account.id
            _append_log(job, f"Account row created (id={account.id})")
            _set_status(db, job, "success")
        except Exception as exc:
            db.rollback()
            logger.exception("[account_creator] failed to persist account")
            _append_log(job, f"Account persistence failed: {exc}")
            db.commit()
            _set_status(db, job, "failed", f"Account persistence failed: {exc}")
    finally:
        db.close()


def _set_phone(db: Session, job: AccountCreationJob, phone: str) -> None:
    job.phone_number = phone
    db.commit()
