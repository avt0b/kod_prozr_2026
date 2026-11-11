from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.reports.domain.report_draft import ReportDraft


@dataclass(frozen=True)
class ReportDraftDTO:
    id: UUID
    person_id: UUID
    text: str
    generator: str
    created_at: datetime

    @classmethod
    def from_entity(cls, draft: ReportDraft) -> "ReportDraftDTO":
        return cls(draft.id, draft.person_id, draft.text, draft.generator, draft.created_at)
