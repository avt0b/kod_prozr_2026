from dataclasses import dataclass
from datetime import datetime

from src.modules.stats.application.interfaces.sources import (
    AppealsCounterInterface,
    OfficialsCounterInterface,
    RiskCounterInterface,
)

SEVERITIES = ("high", "medium", "low")
APPEAL_STATUSES = ("new", "analyzed", "routed", "closed")


@dataclass(frozen=True)
class OverviewDTO:
    officials_total: int
    officials_with_flags: int
    flags_by_severity: dict[str, int]
    appeals_total: int
    appeals_by_status: dict[str, int]
    computed_at: datetime | None


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
        risk = await self._risk.summary()
        appeals = await self._appeals.appeals_by_status()
        # Все ключи всегда на месте: фронт рисует счётчик и для нуля.
        return OverviewDTO(
            officials_total=await self._officials.count_officials(),
            officials_with_flags=risk.flagged_officials,
            flags_by_severity={s: risk.flags_by_severity.get(s, 0) for s in SEVERITIES},
            appeals_total=sum(appeals.values()),
            appeals_by_status={s: appeals.get(s, 0) for s in APPEAL_STATUSES},
            computed_at=risk.computed_at,
        )
