from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.score import RiskScore


class RiskRepositoryInterface(Protocol):
    async def replace_all(self, flags: list[RiskFlag], scores: list[RiskScore]) -> None:
        """Заменить результаты прошлого расчёта целиком. Не коммитит."""
        ...

    async def replace_for_persons(
        self, person_ids: Sequence[UUID], flags: list[RiskFlag], scores: list[RiskScore]
    ) -> None:
        """Заменить флаги и баллы только указанных людей (частичный пересчёт). Не коммитит."""
        ...

    async def get_scores(self, person_ids: Sequence[UUID]) -> list[RiskScore]: ...

    async def get_flags(self, person_ids: Sequence[UUID]) -> list[RiskFlag]: ...

    async def severity_counts(self) -> dict[str, int]: ...

    async def flagged_officials_count(self) -> int: ...
