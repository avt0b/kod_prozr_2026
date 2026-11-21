"""Управление учётными записями: только для администратора (#70)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.core.infrastructure.auth import password_hasher, require_admin
from src.core.infrastructure.database.models.auth import AuthSessionModel, Role, UserModel
from src.core.infrastructure.dependencies import get_session
from src.core.schemas import PageResponse

router = APIRouter(prefix="/admin/users", tags=["Admin"])
DB = Annotated[AsyncSession, Depends(get_session)]
Admin = Annotated[UserModel, Depends(require_admin)]

USERNAME = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")


class AdminUserResponse(BaseModel):
    id: UUID
    username: str
    role: Role
    active: bool


class AdminUserCreate(BaseModel):
    username: str = USERNAME
    password: str = Field(min_length=12, max_length=256)
    role: Role = Role.ANALYST


class AdminUserUpdate(BaseModel):
    role: Role | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=256)


def to_response(user: UserModel) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id, username=user.username, role=Role(user.role), active=user.active
    )


async def get_user_for_update(db: AsyncSession, user_id: UUID) -> UserModel:
    user = (
        await db.execute(select(UserModel).where(UserModel.id == user_id).with_for_update())
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "Пользователь не найден.")
    return user


async def ensure_other_admin(db: AsyncSession, user: UserModel) -> None:
    """Нельзя оставить систему без активного администратора.

    Строки активных админов блокируются, чтобы два админа не разжаловали друг друга одновременно.
    """
    admins = (
        (
            await db.execute(
                select(UserModel.id)
                .where(UserModel.role == Role.ADMIN, UserModel.active.is_(True))
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    if not set(admins) - {user.id}:
        raise HTTPException(409, "Нельзя убрать последнего активного администратора.")


async def revoke_sessions(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(
        update(AuthSessionModel).where(AuthSessionModel.user_id == user_id).values(revoked=True)
    )


@router.get("", response_model=PageResponse[AdminUserResponse])
async def list_users(
    _: Admin,
    db: DB,
    role: Role | None = None,
    query: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[AdminUserResponse]:
    conditions = []
    if role is not None:
        conditions.append(UserModel.role == role)
    if query:
        escaped = query.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(UserModel.username.like(f"%{escaped}%", escape="\\"))
    total = (
        await db.execute(select(func.count()).select_from(UserModel).where(*conditions))
    ).scalar_one()
    users = (
        await db.execute(
            select(UserModel)
            .where(*conditions)
            .order_by(UserModel.username)
            .limit(limit)
            .offset(offset)
        )
    ).scalars()
    return PageResponse(items=[to_response(u) for u in users], total=total)


@router.post("", response_model=AdminUserResponse, status_code=201)
async def create_user(body: AdminUserCreate, _: Admin, db: DB) -> AdminUserResponse:
    username = body.username.lower()
    taken = HTTPException(409, "Этот логин уже занят.")
    if (await db.execute(select(UserModel.id).where(UserModel.username == username))).first():
        raise taken
    user = UserModel(
        username=username,
        password_hash=await run_in_threadpool(password_hasher.hash, body.password),
        active=True,
        role=body.role,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise taken from None
    return to_response(user)


@router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_user(user_id: UUID, body: AdminUserUpdate, _: Admin, db: DB) -> AdminUserResponse:
    """Смена роли, блокировка или новый пароль сразу отзывают все сессии пользователя."""
    user = await get_user_for_update(db, user_id)
    loses_admin = (
        user.role == Role.ADMIN
        and user.active
        and ((body.role is not None and body.role != Role.ADMIN) or body.active is False)
    )
    if loses_admin:
        await ensure_other_admin(db, user)
    changed = False
    if body.role is not None and body.role != user.role:
        user.role, changed = body.role, True
    if body.active is not None and body.active != user.active:
        user.active, changed = body.active, True
    if body.password is not None:
        user.password_hash = await run_in_threadpool(password_hasher.hash, body.password)
        changed = True
    if changed:
        await revoke_sessions(db, user.id)
    await db.commit()
    return to_response(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: UUID, _: Admin, db: DB) -> Response:
    user = await get_user_for_update(db, user_id)
    if user.role == Role.ADMIN and user.active:
        await ensure_other_admin(db, user)
    await db.delete(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            409,
            "У пользователя есть связанные данные (например, схемы графа). "
            "Заблокируйте его вместо удаления.",
        ) from None
    return Response(status_code=204)
