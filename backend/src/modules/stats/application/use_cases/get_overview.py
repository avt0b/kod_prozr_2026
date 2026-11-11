from dataclasses import dataclass

from src.modules.stats.application.interfaces.sources import (
    AppealsCounterInterface,
    OfficialsCounterInterface,
    RiskCounterInterface,
)


@dataclass(frozen=True)
class OverviewDTO:
    officials_total: int
    officials_flagged: int
    flags_by_severity: dict[str, int]
    appeals_by_status: dict[str, int]


class GetOverviewUseCase:
    """GET /stats/overview: счётчики для главной. Своих данных и агрегатов у stats нет."""

    def __init__(
        self,
        officials: OfficialsCounterInterface,
        risk: RiskCounterInterface,
        appeals: AppealsCounterInterface,
    ) -> None:
        self._officials = officials
        self._risk = risk
        self._appeals = appeals

    async def execute(self) -> OverviewDTO:
        return OverviewDTO(
            officials_total=await self._officials.count_officials(),
            officials_flagged=await self._risk.flagged_officials(),
            flags_by_severity=await self._risk.flags_by_severity(),
            appeals_by_status=await self._appeals.appeals_by_status(),
        )
