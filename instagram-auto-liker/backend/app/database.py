from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables and apply lightweight column migrations."""
    from sqlalchemy import text

    from . import models  # noqa: F401  (registers models)

    Base.metadata.create_all(bind=engine)

    _pg_migrations = [
        "ALTER TABLE targets ADD COLUMN IF NOT EXISTS comment_enabled BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE targets ADD COLUMN IF NOT EXISTS comment_templates TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE targets ADD COLUMN IF NOT EXISTS story_watch_enabled BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS encrypted_proxy TEXT",
        # New columns
        "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS proxy_type VARCHAR(20)",
        "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS personality TEXT",
        "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS encrypted_totp_secret TEXT",
    ]
    with engine.begin() as conn:
        for stmt in _pg_migrations:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
