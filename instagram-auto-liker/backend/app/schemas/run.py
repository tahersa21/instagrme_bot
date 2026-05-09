from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.run import RunStatus


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    status: RunStatus
    triggered_by: str
    likes_attempted: int
    likes_succeeded: int
    likes_skipped: int
    likes_failed: int
    started_at: datetime
    finished_at: datetime | None = None
    error: str | None = None


class LikeLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int | None = None
    account_id: int
    target_username: str
    media_id: str
    media_url: str | None = None
    success: bool
    skipped_reason: str | None = None
    error: str | None = None
    created_at: datetime
