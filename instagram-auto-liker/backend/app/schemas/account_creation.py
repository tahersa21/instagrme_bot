"""Pydantic schemas for the account-creation flow."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountCreateRequest(BaseModel):
    domain_id: int
    sms_provider_id: int | None = None
    full_name: str | None = Field(None, max_length=120, description="Auto-generated if omitted")
    username: str | None = Field(
        None,
        min_length=3,
        max_length=30,
        description="Auto-generated if omitted",
    )
    email_local_part: str | None = Field(
        None,
        max_length=64,
        description="Local part of email before @domain. Auto-generated if omitted.",
    )
    password: str | None = Field(None, min_length=8, description="Auto-generated if omitted")
    proxy: str | None = None


class AccountCreationJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    domain_id: int
    sms_provider_id: int | None
    full_name: str
    username: str
    email: str
    phone_number: str | None
    created_account_id: int | None
    error: str | None
    logs: list[dict] = []
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    @classmethod
    def model_validate(cls, obj, **kw):  # type: ignore[override]
        import json

        data = {
            "id": obj.id,
            "status": obj.status,
            "domain_id": obj.domain_id,
            "sms_provider_id": obj.sms_provider_id,
            "full_name": obj.full_name,
            "username": obj.username,
            "email": obj.email,
            "phone_number": obj.phone_number,
            "created_account_id": obj.created_account_id,
            "error": obj.error,
            "started_at": obj.started_at,
            "finished_at": obj.finished_at,
            "created_at": obj.created_at,
        }
        try:
            data["logs"] = json.loads(obj.logs or "[]")
        except Exception:
            data["logs"] = []
        return cls(**data)
