from uuid import UUID

from src.modules.reports.application.dto.report_dto import ReportDraftDTO
from src.modules.reports.application.interfaces.report_repository import (
    ReportRepositoryInterface,
)
from src.modules.reports.domain.exceptions import ReportDraftNotFoundError


class GetReportDraftUseCase:
    def __init__(self, repository: ReportRepositoryInterface) -> None:
        self._repository = repository

    async def execute(self, report_id: UUID) -> ReportDraftDTO:
        draft = await self._repository.get(report_id)
        if draft is None:
            raise ReportDraftNotFoundError(report_id)
        return ReportDraftDTO.from_entity(draft)
