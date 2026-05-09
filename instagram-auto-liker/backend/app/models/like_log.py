from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class LikeLog(Base):
    """Per-post log of like attempts. Used for de-dup and audit."""

    __tablename__ = "like_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_username: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    media_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skipped_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True, nullable=False
    )
