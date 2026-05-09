from pydantic import BaseModel, Field


class ScheduleSettingsIn(BaseModel):
    enabled: bool = False
    interval_hours: int = Field(6, ge=1, le=168)
    daily_like_limit: int = Field(100, ge=1, le=500)
    hourly_like_limit: int = Field(20, ge=1, le=100)
    min_delay_seconds: int = Field(30, ge=5, le=600)
    max_delay_seconds: int = Field(90, ge=5, le=600)
    warmup_enabled: bool = True


class ScheduleSettingsOut(ScheduleSettingsIn):
    pass


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
