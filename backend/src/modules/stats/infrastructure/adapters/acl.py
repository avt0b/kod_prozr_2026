"""ACL stats -> officials / risk / appeals. Внешние источники — локальные протоколы,
настоящие объекты (Query*UseCase модулей) подставляет src/web/dependencies.py."""

from datetime import datetime
from typing import Protocol

from src.modules.stats.application.interfaces.sources import (
    AppealsCounterInterface,
    OfficialsCounterInterface,
    RiskCounterInterface,
    RiskSummary,
)


class ExternalOfficialsSource(Protocol):
    async def count_officials(self) -> int: ...


class ExternalRiskStats(Protocol):
    @property
    def flags_by_severity(self) -> dict[str, int]: ...
    @property
    def flagged_officials(self) -> int: ...
    @property
    def computed_at(self) -> datetime | None: ...


class ExternalRiskSource(Protocol):
    async def stats(self) -> ExternalRiskStats: ...


class ExternalAppealsSource(Protocol):
    async def status_counts(self) -> dict[str, int]: ...


class OfficialsCounterACLAdapter(OfficialsCounterInterface):
    def __init__(self, source: ExternalOfficialsSource) -> None:
        self._source = source

    async def count_officials(self) -> int:
        return await self._source.count_officials()


class RiskCounterACLAdapter(RiskCounterInterface):
    def __init__(self, source: ExternalRiskSource) -> None:
        self._source = source

    async def summary(self) -> RiskSummary:
        stats = await self._source.stats()
        return RiskSummary(
            flags_by_severity=dict(stats.flags_by_severity),
            flagged_officials=stats.flagged_officials,
            computed_at=stats.computed_at,
        )


class AppealsCounterACLAdapter(AppealsCounterInterface):
    def __init__(self, source: ExternalAppealsSource) -> None:
        self._source = source

    async def appeals_by_status(self) -> dict[str, int]:
        return await self._source.status_counts()
