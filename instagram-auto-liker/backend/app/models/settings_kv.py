from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SettingsKV(Base):
    """Key/value store for runtime settings (schedule interval, limits, …)."""

    __tablename__ = "settings_kv"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
