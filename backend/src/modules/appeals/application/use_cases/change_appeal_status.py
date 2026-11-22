from uuid import UUID

from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.modules.appeals.application.dto.appeal_dto import AppealDTO
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.domain.enums import AppealStatus
from src.modules.appeals.domain.exceptions import (
    AppealNotFoundError,
    InvalidAppealStatusTransitionError,
)


class ChangeAppealStatusUseCase:
    """POST /appeals/{id}/status: аналитик передаёт обращение по подведомственности или закрывает.

    Переходы проверяет агрегат: analyzed → routed, любой незакрытый → closed; иначе 409.
    """

    def __init__(
        self,
        repository: AppealRepositoryInterface,
        directory: PersonDirectoryInterface,
        unit_of_work: UnitOfWorkInterface,
    ) -> None:
        self._repository = repository
        self._directory = directory
        self._unit_of_work = unit_of_work

    async def execute(self, appeal_id: UUID, target: AppealStatus) -> AppealDTO:
        async with self._unit_of_work:
            appeal = await self._repository.get(appeal_id)
            if appeal is None:
                raise AppealNotFoundError(appeal_id)
            if target is AppealStatus.ROUTED:
                appeal.route()
            elif target is AppealStatus.CLOSED:
                appeal.close()
            else:
                raise InvalidAppealStatusTransitionError(appeal.status, target)
            await self._repository.save(appeal)
            await self._unit_of_work.commit()
        persons = await self._directory.get_many(appeal.linked_person_ids)
        return AppealDTO.from_entity(appeal, {p.id: p for p in persons})
