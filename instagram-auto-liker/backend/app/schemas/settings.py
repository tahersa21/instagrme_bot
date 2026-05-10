from pydantic import BaseModel, Field


class ScheduleSettingsIn(BaseModel):
    enabled: bool = False
    interval_hours: int = Field(6, ge=1, le=168)
    daily_like_limit: int = Field(100, ge=1, le=500)
    hourly_like_limit: int = Field(20, ge=1, le=100)
    min_delay_seconds: int = Field(30, ge=5, le=600)
    max_delay_seconds: int = Field(90, ge=5, le=600)
    warmup_enabled: bool = True
    # Active-hours window (UTC). Bot only runs within this window.
    active_hours_start: int = Field(8, ge=0, le=23, description="Start of active window (UTC hour)")
    active_hours_end: int = Field(23, ge=0, le=23, description="End of active window (UTC hour)")
    # New-account safety mode: auto-halve limits for accounts < 30 days old
    new_account_mode: bool = True


class ScheduleSettingsOut(ScheduleSettingsIn):
    pass


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
