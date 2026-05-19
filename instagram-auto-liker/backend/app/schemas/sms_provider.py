"""Pydantic schemas for SMS provider (5sim / sms-activate)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

VALID_PROVIDER_TYPES = {"sms-activate", "5sim"}


class SmsProviderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    provider_type: str = Field(..., description="sms-activate | 5sim")
    country_code: str = Field("0", description="Provider-specific country code (0 = any)")
    is_default: bool = False


class SmsProviderCreate(SmsProviderBase):
    api_key: str = Field(..., min_length=8)


class SmsProviderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    provider_type: str | None = None
    api_key: str | None = Field(None, min_length=8)
    country_code: str | None = None
    is_default: bool | None = None


class SmsProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider_type: str
    country_code: str
    is_default: bool
    has_api_key: bool = True
    created_at: datetime
