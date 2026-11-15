from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.core.dto import PageRequest
from src.modules.stats.application.interfaces.risk_map_sources import (
    OfficialPlacement,
    OfficialRiskView,
    PositionView,
)
from src.modules.stats.application.use_cases.get_risk_map import GetRiskMapUseCase
from src.modules.stats.domain.position_risk import (
    PositionRiskLevel,
    position_risk_level,
    typical_risks,
)
from src.modules.stats.domain.risk_map import OfficialRisk, RiskAggregate, RuleCount

COMPUTED_AT = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def _official(name: str, score: float, *rules: str) -> OfficialRisk:
    return OfficialRisk(person_id=uuid4(), full_name=name, score=score, rule_codes=rules)


def test_aggregate_counts_share_scores_and_frequent_rules() -> None:
    officials = [
        _official("Б", 90.0, "R01", "R05"),
        _official("А", 30.0, "R01"),
        _official("В", 0.0),
        _official("Г", 30.0, "R02", "R02"),  # повтор правила у одного служащего считается раз
    ]

    stats = RiskAggregate.of(officials)

    assert stats.officials_total == 4
    assert stats.officials_with_flags == 3
    assert stats.flagged_share == 0.75
    assert stats.avg_score == 37.5
    assert stats.max_score == 90.0
    assert stats.top_rules == (RuleCount("R01", 2), RuleCount("R02", 1), RuleCount("R05", 1))
    # Только служащие с флагами, по баллу, при равенстве — по ФИО.
    assert [o.full_name for o in stats.top_officials] == ["Б", "А", "Г"]


def test_aggregate_of_empty_group_is_zero() -> None:
    stats = RiskAggregate.of([])

    assert (stats.officials_total, stats.flagged_share, stats.avg_score, stats.max_score) == (
        0,
        0.0,
        0.0,
        0.0,
    )
    assert stats.top_rules == () and stats.top_officials == ()


def test_position_level_depends_on_authorities_only() -> None:
    assert position_risk_level(["hr", "procurement"], False) is PositionRiskLevel.HIGH
    assert position_risk_level(["inspection"], False) is PositionRiskLevel.HIGH
    assert position_risk_level(["budget"], False) is PositionRiskLevel.MEDIUM
    assert position_risk_level([], True) is PositionRiskLevel.MEDIUM
    assert position_risk_level([], False) is PositionRiskLevel.LOW


def test_typical_risks_follow_authorities_and_reference_rules_and_law() -> None:
    risks = typical_risks(["procurement", "procurement"])

    assert {r.authority for r in risks} == {"procurement"}
    assert len({r.code for r in risks}) == len(risks)
    assert {"R01", "R06", "R04"} <= {code for r in risks for code in r.rule_codes}
    assert all(r.legal_ref and r.title and r.description for r in risks)
    assert typical_risks([]) == ()
    assert [r.authority for r in typical_risks(["hr", "permits"])][0] == "permits"


class _Placements:
    def __init__(self, items: list[OfficialPlacement]) -> None:
        self._items = items

    async def placements(self) -> list[OfficialPlacement]:
        return self._items


class _Risk:
    def __init__(self, profiles: dict[UUID, OfficialRiskView]) -> None:
        self._profiles = profiles
        self.requested: list[UUID] = []

    async def risk_profiles(self, person_ids: Sequence[UUID]) -> dict[UUID, OfficialRiskView]:
        self.requested = list(person_ids)
        return {pid: p for pid, p in self._profiles.items() if pid in person_ids}

    async def computed_at(self) -> datetime | None:
        return COMPUTED_AT


def _position(title: str, organ_id: UUID, organ: str, *kinds: str) -> PositionView:
    return PositionView(
        id=uuid4(),
        title=title,
        department="Отдел",
        organ_id=organ_id,
        organ_name=organ,
        is_corruption_risky=bool(kinds),
        authority_kinds=kinds,
    )


async def test_use_case_groups_officials_by_position_and_organ() -> None:
    build, health = uuid4(), uuid4()
    buyer = _position("Начальник отдела закупок", build, "Минстрой", "budget", "procurement")
    clerk = _position("Специалист", build, "Минстрой")
    doctor = _position("Главный специалист", health, "Комздрав", "permits")
    people = {name: uuid4() for name in ("Соколов", "Петров", "Иванова", "Орлов")}
    placements = [
        OfficialPlacement(people["Соколов"], "Соколов", buyer),
        OfficialPlacement(people["Петров"], "Петров", buyer),
        OfficialPlacement(people["Иванова"], "Иванова", clerk),
        OfficialPlacement(people["Орлов"], "Орлов", doctor),
    ]
    risk = _Risk(
        {
            people["Соколов"]: OfficialRiskView(people["Соколов"], 93.0, ("R01", "R06")),
            people["Орлов"]: OfficialRiskView(people["Орлов"], 20.0, ("R02",)),
        }
    )
    use_case = GetRiskMapUseCase(_Placements(placements), risk)

    result = await use_case.execute(None, PageRequest(limit=100))

    assert result.total == 3
    assert result.computed_at == COMPUTED_AT
    assert [i.title for i in result.items] == [
        "Начальник отдела закупок",
        "Главный специалист",
        "Специалист",
    ]
    top = result.items[0]
    assert top.authorities == ("procurement", "budget")  # порядок каталога, не источника
    assert top.risk_level == "high"
    assert top.stats.officials_total == 2 and top.stats.officials_with_flags == 1
    assert top.stats.avg_score == 46.5 and top.stats.max_score == 93.0
    assert [o.full_name for o in top.stats.top_officials] == ["Соколов"]
    assert {r.authority for r in top.typical_risks} == {"procurement", "budget"}
    assert result.items[2].risk_level == "low" and result.items[2].typical_risks == ()

    organs = {o.organ: o for o in result.organs}
    assert organs["Минстрой"].positions_total == 2
    assert organs["Минстрой"].stats.officials_total == 3
    assert organs["Комздрав"].stats.top_rules == (RuleCount("R02", 1),)


async def test_use_case_filters_by_organ_and_paginates() -> None:
    build, health = uuid4(), uuid4()
    placements = [
        OfficialPlacement(uuid4(), "А", _position("Должность 1", build, "Минстрой", "hr")),
        OfficialPlacement(uuid4(), "Б", _position("Должность 2", build, "Минстрой")),
        OfficialPlacement(uuid4(), "В", _position("Должность 3", health, "Комздрав")),
    ]
    risk = _Risk({})
    use_case = GetRiskMapUseCase(_Placements(placements), risk)

    result = await use_case.execute(build, PageRequest(limit=1, offset=1))

    assert result.total == 2
    assert [i.title for i in result.items] == ["Должность 2"]
    assert [o.organ for o in result.organs] == ["Минстрой"]
    assert len(risk.requested) == 2  # баллы спрашиваем только для служащих выбранного органа
