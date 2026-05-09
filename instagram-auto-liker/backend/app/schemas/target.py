import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TargetCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    likes_per_run: int = Field(3, ge=1, le=20)
    is_enabled: bool = True
    comment_enabled: bool = False
    comment_templates: list[str] = Field(default_factory=list)
    story_watch_enabled: bool = False


class TargetUpdate(BaseModel):
    likes_per_run: int | None = Field(None, ge=1, le=20)
    is_enabled: bool | None = None
    comment_enabled: bool | None = None
    comment_templates: list[str] | None = None
    story_watch_enabled: bool | None = None


class TargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    username: str
    likes_per_run: int
    is_enabled: bool
    comment_enabled: bool
    comment_templates: list[str]
    story_watch_enabled: bool
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_templates(cls, data: Any) -> Any:
        if hasattr(data, "comment_templates"):
            raw = data.comment_templates
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    parsed = []
                object.__setattr__(data, "comment_templates", parsed)
        return data
