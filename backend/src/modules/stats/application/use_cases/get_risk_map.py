from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.core.dto import PageRequest
from src.modules.stats.application.interfaces.risk_map_sources import (
    OfficialPlacementsInterface,
    OfficialRiskProfilesInterface,
    PositionView,
)
from src.modules.stats.domain.position_risk import (
    TypicalRisk,
    position_risk_level,
    typical_risks,
)
from src.modules.stats.domain.risk_map import OfficialRisk, RiskAggregate

_AUTHORITY_ORDER = ("procurement", "permits", "inspection", "budget", "hr")


@dataclass(frozen=True)
class PositionRiskDTO:
    position_id: UUID
    title: str
    department: str
    organ_id: UUID
    organ: str
    is_corruption_risky: bool
    authorities: tuple[str, ...]
    risk_level: str
    typical_risks: tuple[TypicalRisk, ...]
    stats: RiskAggregate


@dataclass(frozen=True)
class OrganRiskDTO:
    organ_id: UUID
    organ: str
    positions_total: int
    stats: RiskAggregate


@dataclass(frozen=True)
class RiskMapDTO:
    items: list[PositionRiskDTO]
    total: int
    organs: list[OrganRiskDTO]
    computed_at: datetime | None


class GetRiskMapUseCase:
    """GET /risk-map: риск по должностям и органам (вариант D).

    Служащий относится к своей текущей должности — той же, что показывает рейтинг.
    Должности без служащих в карту не попадают: их нет в источнике назначений.
    """

    def __init__(
        self,
        placements: OfficialPlacementsInterface,
        risk: OfficialRiskProfilesInterface,
    ) -> None:
        self._placements = placements
        self._risk = risk

    async def execute(self, organ_id: UUID | None, page: PageRequest) -> RiskMapDTO:
        placements = [
            p
            for p in await self._placements.placements()
            if organ_id is None or p.position.organ_id == organ_id
        ]
        profiles = await self._risk.risk_profiles([p.person_id for p in placements])

        positions: dict[UUID, PositionView] = {}
        by_position: dict[UUID, list[OfficialRisk]] = defaultdict(list)
        by_organ: dict[UUID, list[OfficialRisk]] = defaultdict(list)
        organ_names: dict[UUID, str] = {}
        for placement in placements:
            position = placement.position
            profile = profiles.get(placement.person_id)
            official = OfficialRisk(
                person_id=placement.person_id,
                full_name=placement.full_name,
                score=profile.score if profile else 0.0,
                rule_codes=profile.rule_codes if profile else (),
            )
            positions[position.id] = position
            by_position[position.id].append(official)
            by_organ[position.organ_id].append(official)
            organ_names[position.organ_id] = position.organ_name

        items = [self._position_item(positions[pid], by_position[pid]) for pid in positions]
        # Сверху — должности с наибольшим средним риском, затем по максимуму и названию.
        items.sort(key=lambda i: (-i.stats.avg_score, -i.stats.max_score, i.organ, i.title))

        positions_per_organ: dict[UUID, int] = defaultdict(int)
        for position in positions.values():
            positions_per_organ[position.organ_id] += 1
        organs = [
            OrganRiskDTO(
                organ_id=oid,
                organ=organ_names[oid],
                positions_total=positions_per_organ[oid],
                stats=RiskAggregate.of(officials),
            )
            for oid, officials in by_organ.items()
        ]
        organs.sort(key=lambda o: (-o.stats.avg_score, o.organ))

        return RiskMapDTO(
            items=items[page.offset : page.offset + page.limit],
            total=len(items),
            organs=organs,
            computed_at=await self._risk.computed_at(),
        )

    @staticmethod
    def _position_item(position: PositionView, officials: list[OfficialRisk]) -> PositionRiskDTO:
        kinds = tuple(k for k in _AUTHORITY_ORDER if k in set(position.authority_kinds))
        return PositionRiskDTO(
            position_id=position.id,
            title=position.title,
            department=position.department,
            organ_id=position.organ_id,
            organ=position.organ_name,
            is_corruption_risky=position.is_corruption_risky,
            authorities=kinds,
            risk_level=position_risk_level(kinds, position.is_corruption_risky).value,
            typical_risks=typical_risks(kinds),
            stats=RiskAggregate.of(officials),
        )
