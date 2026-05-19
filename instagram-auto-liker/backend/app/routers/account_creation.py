"""Endpoints to launch and monitor automated Instagram account-creation jobs."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AccountCreationJob, Domain, SmsProvider
from ..schemas.account_creation import AccountCreateRequest, AccountCreationJobOut
from ..services.account_creator import prepare_job_fields, run_account_creation
from ..services.auth import get_current_user
from ..services.crypto import encrypt

router = APIRouter(
    prefix="/api/account-creation",
    tags=["account-creation"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=AccountCreationJobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: AccountCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AccountCreationJobOut:
    domain = db.scalar(select(Domain).where(Domain.id == payload.domain_id))
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    if payload.sms_provider_id is not None:
        sp = db.scalar(select(SmsProvider).where(SmsProvider.id == payload.sms_provider_id))
        if not sp:
            raise HTTPException(status_code=404, detail="SMS provider not found")

    fields = prepare_job_fields(
        domain=domain,
        full_name=payload.full_name,
        username=payload.username,
        email_local_part=payload.email_local_part,
        password=payload.password,
    )

    job = AccountCreationJob(
        domain_id=domain.id,
        sms_provider_id=payload.sms_provider_id,
        full_name=fields["full_name"],
        username=fields["username"],
        email=fields["email"],
        encrypted_password=encrypt(fields["password"]),
        encrypted_proxy=encrypt(payload.proxy) if payload.proxy else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_account_creation, job.id)
    return AccountCreationJobOut.model_validate(job)


@router.get("", response_model=list[AccountCreationJobOut])
def list_jobs(db: Session = Depends(get_db)) -> list[AccountCreationJobOut]:
    rows = db.scalars(
        select(AccountCreationJob).order_by(AccountCreationJob.created_at.desc()).limit(100)
    ).all()
    return [AccountCreationJobOut.model_validate(r) for r in rows]


@router.get("/{job_id}", response_model=AccountCreationJobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> AccountCreationJobOut:
    j = db.scalar(select(AccountCreationJob).where(AccountCreationJob.id == job_id))
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return AccountCreationJobOut.model_validate(j)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)) -> None:
    j = db.scalar(select(AccountCreationJob).where(AccountCreationJob.id == job_id))
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(j)
    db.commit()
