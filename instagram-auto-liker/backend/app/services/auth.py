"""Local web-app auth — protects the dashboard with a username/password
configured in `.env`. Uses a simple JWT bearer token.

This is *not* Instagram auth — it's the login for the management UI itself.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=True)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_admin_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    if username != settings.admin_username:
        return False
    if password == settings.admin_password:
        return True
    try:
        return pwd_context.verify(password, settings.admin_password)
    except Exception:
        return False


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(tz=UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            raise JWTError("missing sub")
        return sub
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
