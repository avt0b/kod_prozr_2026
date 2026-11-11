"""Порты read-side модуля stats к трём контекстам. Реализации — ACL в infrastructure/adapters."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class RiskSummary:
    flags_by_severity: dict[str, int]
    flagged_officials: int
    computed_at: datetime | None


class OfficialsCounterInterface(Protocol):
    async def count_officials(self) -> int: ...


class RiskCounterInterface(Protocol):
    async def summary(self) -> RiskSummary: ...


class AppealsCounterInterface(Protocol):
    async def appeals_by_status(self) -> dict[str, int]: ...
