from collections.abc import Sequence
from uuid import UUID

from src.core.utils.iterables import chunked
from src.modules.appeals.application.dto.appeal_dto import AppealMentionDTO
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)


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
