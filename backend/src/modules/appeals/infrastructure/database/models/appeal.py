from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import TimeStampMixin, UUIDMixin
from src.modules.appeals.domain.appeal import Appeal
from src.modules.appeals.domain.enums import AppealStatus
from src.modules.appeals.infrastructure.database.schema import APPEALS_SCHEMA
from src.modules.appeals.infrastructure.serialization import analysis_from_json, analysis_to_json


class AppealModel(Base, UUIDMixin, TimeStampMixin):
    __tablename__ = "appeals"
    __table_args__ = (
        Index("ix_appeals_linked_person_ids", "linked_person_ids", postgresql_using="gin"),
        {"schema": APPEALS_SCHEMA},
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # Денормализация из analysis — для фильтров списка без разбора JSONB.
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    is_corruption: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Люди из контекста officials: id без внешних ключей.
    linked_person_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(Uuid), nullable=False, server_default="{}"
    )

    def to_entity(self) -> Appeal:
        return Appeal(
            id=self.id,
            text=self.text,
            channel=self.channel,
            received_at=self.received_at,
            status=AppealStatus(self.status),
            analysis=analysis_from_json(self.analysis),
            linked_person_ids=tuple(self.linked_person_ids or ()),
        )

    @staticmethod
    def row(appeal: Appeal) -> dict[str, Any]:
        analysis = appeal.analysis
        return {
            "id": appeal.id,
            "received_at": appeal.received_at,
            "channel": appeal.channel,
            "text": appeal.text,
            "status": appeal.status.value,
            "analysis": analysis_to_json(analysis),
            "category": analysis.category.value if analysis else None,
            "is_corruption": analysis.is_corruption if analysis else None,
            "linked_person_ids": list(appeal.linked_person_ids),
        }
