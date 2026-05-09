from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_active: bool
    last_login_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime


class IGLoginPasswordRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    verification_code: str | None = None


class IGLoginCookiesRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    cookies_json: str = Field(..., min_length=1)


class IGLoginResponse(BaseModel):
    account: AccountOut
    requires_2fa: bool = False
    requires_challenge: bool = False
    message: str | None = None
