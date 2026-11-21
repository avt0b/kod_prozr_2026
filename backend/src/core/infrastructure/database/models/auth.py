from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin


class UserModel(Base, UUIDMixin):
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}

    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    active: Mapped[bool] = mapped_column(default=True)


class AuthSessionModel(Base, UUIDMixin):
    __tablename__ = "auth_sessions"
    __table_args__ = {"schema": "core"}

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("core.users.id", ondelete="CASCADE"))
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    logout_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(default=False)
