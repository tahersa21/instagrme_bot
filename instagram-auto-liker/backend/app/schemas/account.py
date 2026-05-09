from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_active: bool
    has_proxy: bool = False
    last_login_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime

    @classmethod
    def model_validate(cls, obj, **kw):  # type: ignore[override]
        instance = super().model_validate(obj, **kw)
        if hasattr(obj, "encrypted_proxy"):
            instance.has_proxy = bool(obj.encrypted_proxy)
        return instance


class IGLoginPasswordRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    verification_code: str | None = None
    proxy: str | None = None


class IGLoginCookiesRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    cookies_json: str = Field(..., min_length=1)
    proxy: str | None = None


class IGLoginResponse(BaseModel):
    account: AccountOut
    requires_2fa: bool = False
    requires_challenge: bool = False
    message: str | None = None


class ProxyUpdateRequest(BaseModel):
    proxy: str | None = Field(
        None,
        description="Full proxy URL e.g. http://user:pass@host:port or socks5://host:port. Send null to clear.",
    )
