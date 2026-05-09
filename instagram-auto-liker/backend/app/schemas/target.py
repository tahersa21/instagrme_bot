from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TargetCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    likes_per_run: int = Field(3, ge=1, le=20)
    is_enabled: bool = True


class TargetUpdate(BaseModel):
    likes_per_run: int | None = Field(None, ge=1, le=20)
    is_enabled: bool | None = None


class TargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    username: str
    likes_per_run: int
    is_enabled: bool
    created_at: datetime
