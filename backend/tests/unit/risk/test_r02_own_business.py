from datetime import date

from src.modules.risk.domain.enums import RuleCode
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
        today=today, officials=[official], companies=[make_company()], company_roles=[make_role("official")]
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
        today=today, officials=[official], companies=[make_company()], company_roles=[make_role("spouse")]
    )

    assert OwnBusinessRule().evaluate(official, world) == []
