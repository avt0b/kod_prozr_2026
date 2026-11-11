from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.reports.application.interfaces.report_repository import (
    ReportRepositoryInterface,
)
from src.modules.reports.domain.report_draft import ReportDraft
from src.modules.reports.infrastructure.database.models import ReportDraftModel


class ReportRepository(ReportRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, report_id: UUID) -> ReportDraft | None:
        model = await self._session.get(ReportDraftModel, report_id)
        return model.to_entity() if model else None

    async def add(self, draft: ReportDraft) -> None:
        self._session.add(ReportDraftModel.from_entity(draft))
        await self._session.flush()
