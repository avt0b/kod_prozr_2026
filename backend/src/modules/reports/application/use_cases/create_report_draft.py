from uuid import UUID

from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.modules.reports.application.dto.report_dto import ReportDraftDTO
from src.modules.reports.application.interfaces.dossier_source import DossierSourceInterface
from src.modules.reports.application.interfaces.report_repository import (
    ReportRepositoryInterface,
)
from src.modules.reports.application.interfaces.report_writer import ReportWriterInterface
from src.modules.reports.domain.exceptions import ReportSubjectNotFoundError
from src.modules.reports.domain.report_draft import ReportDraft


class CreateReportDraftUseCase:
    """POST /reports {person_id}: досье -> текст (LLM или шаблон) -> сохранить черновик."""

    def __init__(
        self,
        dossiers: DossierSourceInterface,
        writer: ReportWriterInterface,
        repository: ReportRepositoryInterface,
        unit_of_work: UnitOfWorkInterface,
    ) -> None:
        self._dossiers = dossiers
        self._writer = writer
        self._repository = repository
        self._unit_of_work = unit_of_work

    async def execute(self, person_id: UUID) -> ReportDraftDTO:
        dossier = await self._dossiers.get_dossier(person_id)
        if dossier is None:
            raise ReportSubjectNotFoundError(person_id)

        written = await self._writer.write(dossier)  # до транзакции: LLM может быть медленной
        draft = ReportDraft(person_id=person_id, text=written.text, generator=written.generator)

        async with self._unit_of_work:
            await self._repository.add(draft)
            await self._unit_of_work.commit()
        return ReportDraftDTO.from_entity(draft)
