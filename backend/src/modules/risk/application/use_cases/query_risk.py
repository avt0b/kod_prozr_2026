from collections.abc import Sequence
from uuid import UUID

from src.modules.risk.application.dto.risk_dto import RiskFlagDTO, RiskScoreDTO, RiskStatsDTO
from src.modules.risk.application.interfaces.risk_repository import RiskRepositoryInterface


class QueryRiskUseCase:
    """Published language контекста risk для ACL других модулей (officials, reports, stats)."""

    def __init__(self, repository: RiskRepositoryInterface) -> None:
        self._repository = repository

    async def get_scores(self, person_ids: Sequence[UUID]) -> list[RiskScoreDTO]:
        return [RiskScoreDTO.from_entity(s) for s in await self._repository.get_scores(person_ids)]

    async def get_flags(self, person_ids: Sequence[UUID]) -> list[RiskFlagDTO]:
        return [RiskFlagDTO.from_entity(f) for f in await self._repository.get_flags(person_ids)]

    async def stats(self) -> RiskStatsDTO:
        return RiskStatsDTO(
            flags_by_severity=await self._repository.severity_counts(),
            flagged_officials=await self._repository.flagged_officials_count(),
        )
