from uuid import UUID

from src.modules.appeals.application.dto.appeal_dto import AppealDTO
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.domain.exceptions import AppealNotFoundError


class GetAppealUseCase:
    """Обращение с анализом и ФИО привязанных служащих."""

    def __init__(
        self, repository: AppealRepositoryInterface, directory: PersonDirectoryInterface
    ) -> None:
        self._repository = repository
        self._directory = directory

    async def execute(self, appeal_id: UUID) -> AppealDTO:
        appeal = await self._repository.get(appeal_id)
        if appeal is None:
            raise AppealNotFoundError(appeal_id)
        persons = await self._directory.get_many(appeal.linked_person_ids)
        return AppealDTO.from_entity(appeal, {p.id: p for p in persons})
