import hmac
import secrets
from collections import OrderedDict, deque
from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from starlette.concurrency import run_in_threadpool

from src.core.config import Settings
from src.core.infrastructure.auth import (
    COOKIE_NAME,
    COOKIE_PATH,
    current_user,
    decode_access,
    dummy_hash,
    issue_access,
    password_hasher,
    secret_key,
    token_hash,
    unauthorized,
)
from src.core.infrastructure.database.models.auth import AuthSessionModel, UserModel
from src.core.infrastructure.dependencies import get_session, get_settings

router = APIRouter(prefix="/auth", tags=["Auth"])
DB = Annotated[AsyncSession, Depends(get_session)]
Config = Annotated[Settings, Depends(get_settings)]
# Bounded per-process protection. Deployments must also rate-limit at the ingress.
_attempts: OrderedDict[str, deque[float]] = OrderedDict()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    id: UUID
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    session_id: UUID


def check_origin(request: Request, settings: Settings, *, required: bool = False) -> None:
    origin = request.headers.get("origin")
    if (required and not origin) or (origin and origin not in settings.cors_origins):
        raise HTTPException(403, "Источник запроса не разрешён.")


def throttle(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    now = monotonic()
    attempts = _attempts.setdefault(key, deque())
    _attempts.move_to_end(key)
    while attempts and attempts[0] < now - 60:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(429, "Слишком много попыток. Повторите через минуту.")
    attempts.append(now)
    while len(_attempts) > 10000:
        _attempts.popitem(last=False)


def token_response(user: UserModel, session: AuthSessionModel, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=issue_access(user, session, settings),
        expires_in=settings.auth_access_seconds,
        user=UserResponse(id=user.id, username=user.username),
        session_id=session.id,
    )


def set_refresh(response: Response, token: str, settings: Settings) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
        max_age=settings.auth_refresh_days * 86400,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, response: Response, db: DB, settings: Config
) -> TokenResponse:
    check_origin(request, settings)
    throttle(request)
    secret_key(settings)
    user = (
        await db.execute(select(UserModel).where(UserModel.username == body.username.lower()))
    ).scalar_one_or_none()
    valid = await run_in_threadpool(
        password_hasher.verify, body.password, user.password_hash if user else dummy_hash
    )
    if not valid or user is None or not user.active:
        raise HTTPException(401, "Неверный логин или пароль.")
    session_id, proof = uuid4(), secrets.token_urlsafe(32)
    refresh = f"{session_id}.{proof}.{secrets.token_urlsafe(32)}"
    session = AuthSessionModel(
        id=session_id,
        logout_hash=token_hash(proof),
        user_id=user.id,
        refresh_hash=token_hash(refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.auth_refresh_days),
        revoked=False,
    )
    db.add(session)
    await db.flush()
    result = token_response(user, session, settings)
    await db.commit()
    set_refresh(response, refresh, settings)
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(
    request: Request, response: Response, db: DB, settings: Config
) -> TokenResponse:
    check_origin(request, settings, required=True)
    raw = request.cookies.get(COOKIE_NAME)
    if not raw or len(raw) > 256:
        raise unauthorized()
    try:
        session_id, proof, _ = raw.split(".")
        identifier = UUID(session_id)
    except (ValueError, TypeError):
        raise unauthorized() from None
    session = (
        await db.execute(
            select(AuthSessionModel).where(AuthSessionModel.id == identifier).with_for_update()
        )
    ).scalar_one_or_none()
    if (
        session is None
        or session.revoked
        or session.expires_at <= datetime.now(UTC)
        or not hmac.compare_digest(session.refresh_hash, token_hash(raw))
    ):
        raise unauthorized()
    user = await db.get(UserModel, session.user_id)
    if user is None or not user.active:
        raise unauthorized()
    refresh = f"{session.id}.{proof}.{secrets.token_urlsafe(32)}"
    session.refresh_hash = token_hash(refresh)
    result = token_response(user, session, settings)
    await db.commit()
    # Sliding cookie lifetime cannot extend the fixed server-side session expiry.
    set_refresh(response, refresh, settings)
    return result


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: DB, settings: Config) -> None:
    check_origin(request, settings, required=True)
    raw = request.cookies.get(COOKIE_NAME)
    conditions: list[ColumnElement[bool]] = []
    if raw and len(raw) <= 256:
        try:
            session_id, proof, _ = raw.split(".")
            identifier = UUID(session_id)
            conditions.append(
                (AuthSessionModel.id == identifier)
                & (AuthSessionModel.logout_hash == token_hash(proof))
            )
        except (ValueError, TypeError):
            pass
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        try:
            claims = decode_access(authorization[7:], settings)
            conditions.append(AuthSessionModel.id == UUID(claims["sid"]))
        except HTTPException as error:
            if error.status_code != 401:
                raise
    if conditions:
        await db.execute(update(AuthSessionModel).where(or_(*conditions)).values(revoked=True))
        await db.commit()
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[UserModel, Depends(current_user)], response: Response) -> UserResponse:
    response.headers["Cache-Control"] = "no-store"
    return UserResponse(id=user.id, username=user.username)
