"""AccountCreationJob model: tracks the lifecycle of an Instagram account-creation attempt."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AccountCreationJob(Base):
    __tablename__ = "account_creation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    # pending | running | email_otp_wait | phone_otp_wait | success | failed

    domain_id: Mapped[int] = mapped_column(Integer, ForeignKey("domains.id"))
    sms_provider_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sms_providers.id"), nullable=True
    )

    full_name: Mapped[str] = mapped_column(String(120))
    username: Mapped[str] = mapped_column(String(60), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    encrypted_password: Mapped[str] = mapped_column(Text)
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    encrypted_proxy: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=True
    )

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of log entries

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
