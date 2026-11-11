from src.core.dto import Page, PageRequest
from src.modules.appeals.application.dto.appeal_dto import AppealDTO
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.domain.enums import AppealCategory, AppealStatus


class ListAppealsUseCase:
    def __init__(
        self, repository: AppealRepositoryInterface, directory: PersonDirectoryInterface
    ) -> None:
        self._repository = repository
        self._directory = directory

    async def execute(
        self,
        page: PageRequest,
        status: AppealStatus | None = None,
        category: AppealCategory | None = None,
    ) -> Page[AppealDTO]:
        result = await self._repository.list_page(page, status=status, category=category)
        person_ids = list({p for a in result.items for p in a.linked_person_ids})
        persons = {p.id: p for p in await self._directory.get_many(person_ids)}
        return Page(
            items=[AppealDTO.from_entity(a, persons) for a in result.items], total=result.total
        )
