"""ACL stats -> officials / risk / appeals. Внешние источники — локальные протоколы,
настоящие объекты (Query*UseCase модулей) подставляет src/web/dependencies.py."""

from typing import Protocol

from src.modules.stats.application.interfaces.sources import (
    AppealsCounterInterface,
    OfficialsCounterInterface,
    RiskCounterInterface,
)


class ExternalOfficialsSource(Protocol):
    async def count_officials(self) -> int: ...


class ExternalRiskStats(Protocol):
    @property
    def flags_by_severity(self) -> dict[str, int]: ...
    @property
    def flagged_officials(self) -> int: ...


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

    async def flags_by_severity(self) -> dict[str, int]:
        return dict((await self._source.stats()).flags_by_severity)

    async def flagged_officials(self) -> int:
        return (await self._source.stats()).flagged_officials


class AppealsCounterACLAdapter(AppealsCounterInterface):
    def __init__(self, source: ExternalAppealsSource) -> None:
        self._source = source

    async def appeals_by_status(self) -> dict[str, int]:
        return await self._source.status_counts()
