from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin
from src.modules.reports.domain.report_draft import ReportDraft
from src.modules.reports.infrastructure.database.schema import REPORTS_SCHEMA


class ReportDraftModel(Base, UUIDMixin):
    __tablename__ = "report_drafts"
    __table_args__ = {"schema": REPORTS_SCHEMA}

    # Служащий из контекста officials: id без внешнего ключа.
    person_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    generator: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_entity(self) -> ReportDraft:
        return ReportDraft(
            id=self.id,
            person_id=self.person_id,
            text=self.text,
            generator=self.generator,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, draft: ReportDraft) -> "ReportDraftModel":
        return cls(
            id=draft.id,
            person_id=draft.person_id,
            text=draft.text,
            generator=draft.generator,
            created_at=draft.created_at,
        )
