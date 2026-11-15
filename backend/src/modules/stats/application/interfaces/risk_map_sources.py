"""Порты карты рисков к officials и risk. Реализации — ACL в infrastructure/adapters."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PositionView:
    id: UUID
    title: str
    department: str
    organ_id: UUID
    organ_name: str
    is_corruption_risky: bool
    authority_kinds: tuple[str, ...]


@dataclass(frozen=True)
class OfficialPlacement:
    """Служащий и его текущая должность (как в рейтинге: последняя действующая)."""

    person_id: UUID
    full_name: str
    position: PositionView


@dataclass(frozen=True)
class OfficialRiskView:
    person_id: UUID
    score: float
    rule_codes: tuple[str, ...]


class OfficialPlacementsInterface(Protocol):
    async def placements(self) -> list[OfficialPlacement]: ...


class OfficialRiskProfilesInterface(Protocol):
    async def risk_profiles(self, person_ids: Sequence[UUID]) -> dict[UUID, OfficialRiskView]: ...

    async def computed_at(self) -> datetime | None: ...
