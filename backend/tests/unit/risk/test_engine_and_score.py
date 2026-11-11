from datetime import UTC, date, datetime

from src.modules.risk.domain.engine import RiskEngine
from src.modules.risk.domain.rules import default_rules
from src.modules.risk.domain.score import ScorePolicy
from src.modules.risk.domain.world import RiskWorld
from tests.unit.risk.conftest import make_company, make_contract, make_official, make_role


def test_engine_scores_official_with_r01_and_r02(today: date) -> None:
    official = make_official()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        company_roles=[make_role("official", "director")],
        contracts=[make_contract("c1", date(2023, 4, 18))],
    )
    computed_at = datetime(2026, 11, 11, tzinfo=UTC)

    assessment = RiskEngine(default_rules()).assess(world, computed_at)

    assert sorted(f.rule_code.value for f in assessment.flags) == ["R01", "R02"]
    assert assessment.scores[0].score == 80.0
    assert all(f.computed_at == computed_at for f in assessment.flags)


def test_score_is_capped_at_100() -> None:
    policy = ScorePolicy()
    official = make_official()
    world = RiskWorld(
        today=date(2026, 11, 11),
        officials=[official],
        companies=[make_company()],
        company_roles=[make_role("official", "director")],
        contracts=[make_contract("c1", date(2023, 4, 18))],
    )
    flags = RiskEngine(default_rules()).assess(world).flags * 3

    assert policy.score(official.person.id, flags, datetime.now(UTC)).score == 100.0
