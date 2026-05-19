"""SmsProvider model: stores SMS verification provider API credentials."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SmsProvider(Base):
    __tablename__ = "sms_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    provider_type: Mapped[str] = mapped_column(String(40))  # "sms-activate" | "5sim"
    encrypted_api_key: Mapped[str] = mapped_column(Text)
    country_code: Mapped[str] = mapped_column(String(10), default="0")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
