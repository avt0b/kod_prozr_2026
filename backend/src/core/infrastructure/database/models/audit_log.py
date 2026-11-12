from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin


class AuditLogModel(Base, UUIDMixin):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_object_at", "object_id", "at"),
        {"schema": "core"},
    )
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="analyst")
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
