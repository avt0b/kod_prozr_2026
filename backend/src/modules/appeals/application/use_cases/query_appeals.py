from collections.abc import Sequence
from uuid import UUID

from src.core.dto.page import PageRequest
from src.core.utils.iterables import chunked
from src.modules.appeals.application.dto.appeal_dto import AppealDTO, AppealMentionDTO
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.domain.enums import AppealCategory, AppealStatus


class QueryAppealsUseCase:
    """Published language контекста appeals для ACL других модулей (risk, stats)."""

    def __init__(self, repository: AppealRepositoryInterface) -> None:
        self._repository = repository

    async def mentions(self, person_ids: Sequence[UUID]) -> list[AppealMentionDTO]:
        wanted = set(person_ids)
        result: list[AppealMentionDTO] = []
        for batch in chunked(list(person_ids)):
            for appeal in await self._repository.linked_to(batch):
                analysis = appeal.analysis
                for person_id in appeal.linked_person_ids:
                    if person_id not in wanted:
                        continue
                    result.append(
                        AppealMentionDTO(
                            appeal_id=appeal.id,
                            person_id=person_id,
                            is_corruption=bool(analysis and analysis.is_corruption),
                            category=analysis.category.value if analysis else None,
                            confidence=analysis.confidence if analysis else 0.0,
                            specificity=analysis.specificity if analysis else 0.0,
                            received_at=appeal.received_at,
                            summary=analysis.summary if analysis else None,
                        )
                    )
        # одно обращение может прийти в двух пачках — убираем дубли
        unique = {(m.appeal_id, m.person_id): m for m in result}
        return list(unique.values())

    async def status_counts(self) -> dict[str, int]:
        return await self._repository.status_counts()

    async def search(
        self, person_id: UUID | None, category: str | None, status: str | None, limit: int
    ) -> list[AppealDTO]:
        if not 1 <= limit <= 20:
            raise ValueError("limit must be 1..20")
        category_enum = AppealCategory(category) if category else None
        status_enum = AppealStatus(status) if status else None
        if person_id is None:
            page = await self._repository.list_page(
                PageRequest(limit=min(limit, 20)), status=status_enum, category=category_enum
            )
            appeals = page.items
        else:
            appeals = [
                a
                for a in await self._repository.linked_to([person_id])
                if (status_enum is None or a.status == status_enum)
                and (category_enum is None or (a.analysis and a.analysis.category == category_enum))
            ][:limit]
        return [AppealDTO.from_entity(a) for a in appeals]
