from typing import Protocol
from uuid import UUID

from src.modules.reports.domain.report_draft import ReportDraft


class ReportRepositoryInterface(Protocol):
    async def get(self, report_id: UUID) -> ReportDraft | None: ...

    async def add(self, draft: ReportDraft) -> None:
        """Не коммитит."""
        ...
