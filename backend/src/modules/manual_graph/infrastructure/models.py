from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin


class WorkspaceModel(Base, UUIDMixin):
    __tablename__ = "workspaces"
    __table_args__ = (Index("ix_workspaces_official", "official_id"), {"schema": "manual_graph"})
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("core.users.id"))
    official_id: Mapped[UUID] = mapped_column(Uuid)
    title: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class NodeModel(Base, UUIDMixin):
    __tablename__ = "nodes"
    __table_args__ = {"schema": "manual_graph"}
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("manual_graph.workspaces.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    label: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    source: Mapped[str] = mapped_column(String(500), default="")


class EdgeModel(Base, UUIDMixin):
    __tablename__ = "edges"
    __table_args__ = {"schema": "manual_graph"}
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("manual_graph.workspaces.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[UUID] = mapped_column(Uuid)
    target_id: Mapped[UUID] = mapped_column(Uuid)
    label: Mapped[str] = mapped_column(String(160))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    source: Mapped[str] = mapped_column(String(500), default="")


class ShareModel(Base):
    __tablename__ = "shares"
    __table_args__ = {"schema": "manual_graph"}
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("manual_graph.workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("core.users.id", ondelete="CASCADE"), primary_key=True
    )
