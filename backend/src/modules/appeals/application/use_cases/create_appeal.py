from src.core.events.event_bus import EventBus
from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.modules.appeals.application.dto.appeal_dto import AppealDTO
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.application.services.appeal_analysis import AppealAnalysisService
from src.modules.appeals.domain.appeal import Appeal


class CreateAppealUseCase:
    """POST /appeals: создать обращение, проанализировать, привязать служащих.

    Анализ (LLM может думать десятки секунд) идёт до транзакции. После коммита публикуется
    AppealAnalyzedEvent — подписчик синхронно пересчитывает риск привязанных (ADR-10).
    """

    def __init__(
        self,
        repository: AppealRepositoryInterface,
        analysis: AppealAnalysisService,
        directory: PersonDirectoryInterface,
        unit_of_work: UnitOfWorkInterface,
        event_bus: EventBus,
    ) -> None:
        self._repository = repository
        self._analysis = analysis
        self._directory = directory
        self._unit_of_work = unit_of_work
        self._event_bus = event_bus

    async def execute(self, text: str, channel: str) -> AppealDTO:
        appeal = Appeal(text=text, channel=channel)
        await self._analysis.analyze(appeal)

        async with self._unit_of_work:
            await self._repository.save(appeal)
            await self._unit_of_work.commit()

        await self._event_bus.publish_all(appeal.domain_events)
        appeal.clear_events()

        persons = await self._directory.get_many(appeal.linked_person_ids)
        return AppealDTO.from_entity(appeal, {p.id: p for p in persons})
