from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.officials.application.dto.officials_dto import OfficialRiskDTO, RiskFlagView


class RiskSourceInterface(Protocol):
    """Что officials нужно от контекста risk. Реализация — ACL-адаптер, связка — src/web."""

    async def get_scores(self, person_ids: Sequence[UUID]) -> dict[UUID, float]:
        """Риск-балл по каждому из person_ids; нет расчёта — нет ключа."""
        ...

    async def get_top_flags(
        self, person_ids: Sequence[UUID], per_person: int
    ) -> dict[UUID, tuple[RiskFlagView, ...]]: ...

    async def get_official_risk(self, person_id: UUID) -> OfficialRiskDTO: ...
