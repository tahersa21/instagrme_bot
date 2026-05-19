"""Pydantic schemas for Domain (email reception via Mailgun)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DomainBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="e.g. mydomain.com")
    mailgun_domain: str = Field(..., min_length=3, max_length=255, description="e.g. mg.mydomain.com")
    is_default: bool = False
    notes: str | None = None


class DomainCreate(DomainBase):
    mailgun_api_key: str = Field(..., min_length=10, description="Mailgun Private API key")


class DomainUpdate(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=255)
    mailgun_domain: str | None = Field(None, min_length=3, max_length=255)
    mailgun_api_key: str | None = Field(None, min_length=10)
    is_default: bool | None = None
    notes: str | None = None


class DomainOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    mailgun_domain: str
    is_default: bool
    notes: str | None
    has_api_key: bool = True
    created_at: datetime
