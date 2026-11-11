"""Порты read-side модуля stats к трём контекстам. Реализации — ACL в infrastructure/adapters."""

from typing import Protocol


class OfficialsCounterInterface(Protocol):
    async def count_officials(self) -> int: ...


class RiskCounterInterface(Protocol):
    async def flags_by_severity(self) -> dict[str, int]: ...

    async def flagged_officials(self) -> int: ...


class AppealsCounterInterface(Protocol):
    async def appeals_by_status(self) -> dict[str, int]: ...
