from dataclasses import replace
from datetime import date

from src.modules.risk.domain.enums import RuleCode, Severity
from src.modules.risk.domain.rules.r02_own_business import OwnBusinessRule
from src.modules.risk.domain.world import RiskWorld
from tests.unit.risk.conftest import make_company, make_official, make_role


def test_r02_fires_for_director_of_active_company(today: date) -> None:
    official = make_official()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        company_roles=[make_role("official", "director")],
    )

    flags = OwnBusinessRule().evaluate(official, world)

    assert [f.rule_code for f in flags] == [RuleCode.R02]
    assert "руководителем" in flags[0].explanation
    assert flags[0].legal_ref == "79-ФЗ ст. 17"


def test_r02_founder_explanation_mentions_trust_management(today: date) -> None:
    official = make_official()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        company_roles=[make_role("official")],
    )

    flags = OwnBusinessRule().evaluate(official, world)

    assert len(flags) == 1
    assert "доверительное управление" in flags[0].explanation


def test_r02_ignores_liquidated_company(today: date) -> None:
    official = make_official()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company(status="liquidated")],
        company_roles=[make_role("official", "director")],
    )

    assert OwnBusinessRule().evaluate(official, world) == []


def test_r02_ignores_relatives_business(today: date) -> None:
    official = make_official()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        company_roles=[make_role("spouse")],
    )

    assert OwnBusinessRule().evaluate(official, world) == []


def test_r02_founder_only_is_medium_and_director_is_high(today: date) -> None:
    official = make_official()

    def severity_for(*roles: str) -> list[Severity]:
        world = RiskWorld(
            today=today,
            officials=[official],
            companies=[make_company()],
            company_roles=[make_role("official", role) for role in roles],
        )
        return [f.severity for f in OwnBusinessRule().evaluate(official, world)]

    assert severity_for("founder") == [Severity.MEDIUM]
    assert severity_for("director") == [Severity.HIGH]
    # Учредитель и директор одной компании — один флаг, а не два.
    assert severity_for("founder", "director") == [Severity.HIGH]


def test_r02_ignores_role_that_ended(today: date) -> None:
    official = make_official()
    ended = replace(make_role("official", "director"), ended_at=date(2020, 1, 1))
    world = RiskWorld(
        today=today, officials=[official], companies=[make_company()], company_roles=[ended]
    )

    assert OwnBusinessRule().evaluate(official, world) == []


def test_r02_ignores_former_official(today: date) -> None:
    official = make_official()
    former = replace(
        official,
        appointments=tuple(replace(a, ended_at=date(2024, 1, 1)) for a in official.appointments),
    )
    world = RiskWorld(
        today=today,
        officials=[former],
        companies=[make_company()],
        company_roles=[make_role("official", "director")],
    )

    assert OwnBusinessRule().evaluate(former, world) == []
