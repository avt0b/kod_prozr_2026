import hashlib
import secrets
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.infrastructure.database.models.auth import AuthSessionModel, Role, UserModel
from src.core.infrastructure.dependencies import get_session, get_settings

password_hasher = PasswordHash.recommended()
dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))
bearer = HTTPBearer(auto_error=False)
COOKIE_NAME = "kodprozr_refresh"
COOKIE_PATH = "/api/v1/auth"


def unauthorized() -> HTTPException:
    return HTTPException(
        401, "Сессия недействительна. Войдите снова.", headers={"WWW-Authenticate": "Bearer"}
    )


def secret_key(settings: Settings) -> str:
    key = settings.auth_secret.get_secret_value() if settings.auth_secret else ""
    if len(key) < 32:
        raise HTTPException(503, "Вход временно недоступен: требуется настройка сервера.")
    return key


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_access(user: UserModel, session: AuthSessionModel, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "sid": str(session.id),
            "type": "access",
            "iss": "kod-prozr",
            "aud": "kod-prozr-api",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(seconds=settings.auth_access_seconds),
        },
        secret_key(settings),
        algorithm="HS256",
    )


def decode_access(token: str, settings: Settings) -> dict[str, Any]:
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            secret_key(settings),
            algorithms=["HS256"],
            issuer="kod-prozr",
            audience="kod-prozr-api",
            options={"require": ["exp", "iat", "nbf", "sub", "sid", "type"]},
        )
        if claims["type"] != "access":
            raise unauthorized()
        UUID(claims["sub"])
        UUID(claims["sid"])
        return claims
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized() from None


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> UserModel:
    if credentials is None:
        raise unauthorized()
    claims = decode_access(credentials.credentials, settings)
    row = await db.execute(
        select(UserModel)
        .join(AuthSessionModel, AuthSessionModel.user_id == UserModel.id)
        .where(
            UserModel.id == UUID(claims["sub"]),
            UserModel.active.is_(True),
            AuthSessionModel.id == UUID(claims["sid"]),
            AuthSessionModel.revoked.is_(False),
            AuthSessionModel.expires_at > datetime.now(UTC),
        )
    )
    user = row.scalar_one_or_none()
    if user is None:
        raise unauthorized()
    return user


def forbidden() -> HTTPException:
    return HTTPException(403, "Недостаточно прав для этого действия.")


def require_roles(*roles: Role) -> Callable[..., Awaitable[UserModel]]:
    """Зависимость: активный пользователь с одной из ролей, иначе 403."""
    allowed = frozenset(roles)

    async def dependency(user: Annotated[UserModel, Depends(current_user)]) -> UserModel:
        if user.role not in allowed:
            raise forbidden()
        return user

    return dependency


# Администратор видит всё, что видит аналитик (рабочее место) — плюс управление учётками.
require_staff = require_roles(Role.ANALYST, Role.ADMIN)
require_admin = require_roles(Role.ADMIN)
require_citizen = require_roles(Role.CITIZEN)
