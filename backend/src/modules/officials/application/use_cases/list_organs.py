from src.core.dto import Page, PageRequest
from src.modules.officials.application.dto.mappers import to_organ_dto
from src.modules.officials.application.dto.officials_dto import OrganDTO
from src.modules.officials.application.interfaces.organ_repository import (
    OrganRepositoryInterface,
)


class ListOrgansUseCase:
    def __init__(self, organ_repository: OrganRepositoryInterface) -> None:
        self._organs = organ_repository

    async def execute(self, page: PageRequest) -> Page[OrganDTO]:
        result = await self._organs.list_page(page)
        return Page(items=[to_organ_dto(o) for o in result.items], total=result.total)
