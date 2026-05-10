from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_active: bool
    has_proxy: bool = False
    has_totp: bool = False
    proxy_type: str | None = None
    personality: str | None = None
    last_login_at: datetime | None = None
    last_error: str | None = None
    session_renewed_at: datetime | None = None
    created_at: datetime

    @classmethod
    def model_validate(cls, obj, **kw):  # type: ignore[override]
        instance = super().model_validate(obj, **kw)
        if hasattr(obj, "encrypted_proxy"):
            instance.has_proxy = bool(obj.encrypted_proxy)
        if hasattr(obj, "encrypted_totp_secret"):
            instance.has_totp = bool(obj.encrypted_totp_secret)
        return instance


class IGLoginPasswordRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    verification_code: str | None = None
    totp_secret: str | None = None
    proxy: str | None = None
    proxy_type: str | None = None


class IGLoginCookiesRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    cookies_json: str = Field(..., min_length=1)
    proxy: str | None = None
    proxy_type: str | None = None


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
    proxy_type: str | None = Field(None, description="residential | mobile_4g | datacenter")


class PersonalityUpdateRequest(BaseModel):
    skip_rate: float = Field(0.15, ge=0.05, le=0.35, description="Fraction of posts to skip randomly (5%-35%)")
    session_style: str = Field("moderate", description="active | moderate | quiet")
    warmup_count: int = Field(3, ge=1, le=5, description="Number of warm-up actions before engaging")


class IGLoginPlaywrightRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    verification_code: str | None = None
    totp_secret: str | None = None
    proxy: str | None = None
    proxy_type: str | None = None


class TOTPUpdateRequest(BaseModel):
    totp_secret: str | None = Field(
        None,
        description="Base32 TOTP secret from authenticator app. Send null to remove.",
    )
