from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Account(Base):
    """Stores an Instagram account session.

    Sensitive fields (`encrypted_password`, `encrypted_session`) are encrypted
    with Fernet before being persisted.
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    encrypted_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_session: Mapped[str | None] = mapped_column(Text, nullable=True)

    encrypted_proxy: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Proxy type for UI display & safety scoring
    proxy_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # residential|mobile_4g|datacenter

    # Per-account personality profile (JSON string)
    # {"skip_rate": 0.15, "session_style": "moderate", "warmup_count": 3}
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fernet-encrypted TOTP secret (Base32) for accounts with 2FA enabled
    # Allows automatic 6-digit code generation at login time
    encrypted_totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Set whenever the session is auto-renewed by the liker job
    session_renewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
