from datetime import UTC, date, datetime
from typing import ClassVar

import pytest

from src.modules.risk.domain.engine import RiskEngine
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import OfficialFacts
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.rules import default_rules
from src.modules.risk.domain.rules.base import RiskRule, person_node
from src.modules.risk.domain.score import ScorePolicy
from src.modules.risk.domain.world import RiskWorld
from tests.unit.risk.conftest import make_company, make_contract, make_official, make_role, uid

NOW = datetime(2026, 11, 11, tzinfo=UTC)
PERSON = uid("official")


def _flag(code: RuleCode, weight: float, severity: Severity = Severity.HIGH) -> RiskFlag:
    return RiskFlag(
        person_id=PERSON,
        rule_code=code,
        rule_name=code.value,
        severity=severity,
        weight=weight,
        explanation="тест",
        evidence=(EvidenceNode(NodeType.PERSON, PERSON, "Иванов П.С."),),
    )


class _StubRule(RiskRule):
    """Правило-заглушка: всегда даёт один low-флаг."""

    code: ClassVar[RuleCode] = RuleCode.R06
    name: ClassVar[str] = "stub"
    severity: ClassVar[Severity] = Severity.LOW

    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        return [self.make_flag(official, "заглушка", [person_node(official.person)])]


def test_weights_follow_methodology() -> None:
    policy = ScorePolicy()

    assert policy.weight_for(Severity.HIGH) == 40
    assert policy.weight_for(Severity.MEDIUM) == 20
    assert policy.weight_for(Severity.LOW) == 5
    assert policy.weight_for(Severity.LOW, RuleCode.R08) == 3
    assert policy.weight_for(Severity.MEDIUM, RuleCode.R08) == 5
    assert policy.weight_for(Severity.HIGH, RuleCode.R08) == 5


def test_score_sums_contributions_of_different_rules() -> None:
    flags = [_flag(RuleCode.R01, 40), _flag(RuleCode.R05, 20), _flag(RuleCode.R06, 5)]

    score = ScorePolicy().score(PERSON, flags, NOW)

    assert score.score == 65.0
    assert score.flags_count == 3


def test_repeated_flags_of_one_rule_add_half_weight() -> None:
    flags = [_flag(RuleCode.R05, 20), _flag(RuleCode.R05, 20)]

    assert ScorePolicy().score(PERSON, flags, NOW).score == 30.0


def test_one_rule_contributes_at_most_two_weights() -> None:
    flags = [_flag(RuleCode.R05, 20)] * 10

    assert ScorePolicy().score(PERSON, flags, NOW).score == 40.0


def test_score_is_capped_at_100() -> None:
    flags = [_flag(RuleCode.R01, 40), _flag(RuleCode.R02, 40), _flag(RuleCode.R07, 40)]

    assert ScorePolicy().score(PERSON, flags, NOW).score == 100.0


def test_ml_alone_cannot_lift_official_high() -> None:
    policy = ScorePolicy()
    weight = policy.weight_for(Severity.MEDIUM, RuleCode.R08)

    score = policy.score(PERSON, [_flag(RuleCode.R08, weight, Severity.MEDIUM)] * 3, NOW)

    assert score.score <= 20


def test_no_flags_gives_zero() -> None:
    score = ScorePolicy().score(PERSON, [], NOW)

    assert score.score == 0
    assert score.flags_count == 0


@pytest.mark.parametrize("weights, expected", [([40, 20], 50), ([5, 5, 5], 10), ([], 0)])
def test_rule_contribution(weights: list[float], expected: float) -> None:
    assert ScorePolicy().rule_contribution(weights) == expected


def test_stub_rule_from_registry_gets_into_recompute(today: date) -> None:
    world = RiskWorld(today=today, officials=[make_official()])

    assessment = RiskEngine([_StubRule()]).assess(world, NOW)

    assert [f.rule_code for f in assessment.flags] == [RuleCode.R06]
    assert assessment.flags[0].weight == 5
    assert assessment.scores[0].score == 5.0


def test_engine_scores_official_with_r01_and_r02(today: date) -> None:
    official = make_official()
    world = RiskWorld(
        today=today,
        officials=[official],
        companies=[make_company()],
        company_roles=[make_role("official", "director")],
        contracts=[make_contract("c1", date(2023, 4, 18))],
    )

    assessment = RiskEngine(default_rules()).assess(world, NOW)

    assert sorted(f.rule_code.value for f in assessment.flags) == ["R01", "R02"]
    assert assessment.scores[0].score == 80.0
    assert all(f.computed_at == NOW for f in assessment.flags)


# --- Калибровка B-17 (ADR-16): профили флагов демо-кейсов из data/generated/_truth -----------

H, M, L = Severity.HIGH, Severity.MEDIUM, Severity.LOW
R = RuleCode


def _profile(*flags: tuple[RuleCode, Severity]) -> float:
    policy = ScorePolicy()
    built = [_flag(code, policy.weight_for(sev, code), sev) for code, sev in flags]
    return policy.score(PERSON, built, NOW).score


# Две отдельные схемы над Соколовым до обращения и ближайший кейс под ним.
X1 = _profile((R.R01, H), (R.R02, H))  # учредитель + родственник-поставщик
X2 = _profile((R.R01, H), (R.R03, M), (R.R05, M))
R01_CHILD = _profile((R.R01, H), (R.R07, M))


@pytest.mark.parametrize("r08", [L, M], ids=["r08_low", "r08_medium"])
def test_demo_h1_is_third_before_appeal_and_first_after(r08: Severity) -> None:
    """H1: R01 + R05 + R06 + R07 (два расплывчатых обращения -> low) + R08.

    До демо-обращения он ниже двух схем X1/X2 и выше следующего кейса с запасом ≥ 5 баллов,
    даже если R08 даст medium. После конкретного обращения (R07 -> medium) — 1-й с отрывом ≥ 5.
    """
    before = _profile((R.R01, H), (R.R05, M), (R.R06, L), (R.R07, L), (R.R08, r08))
    after = _profile((R.R01, H), (R.R05, M), (R.R06, L), (R.R07, M), (R.R08, r08))

    assert min(X1, X2) - before >= 5
    assert before - R01_CHILD >= 5
    assert after - max(X1, X2) >= 5


def test_weak_signals_never_outweigh_a_medium_rule() -> None:
    policy = ScorePolicy()
    weak = 2 * policy.weight_for(L) + policy.weight_for(M, R.R08)

    assert weak <= policy.weight_for(M) - 5
    assert policy.weight_for(M, R.R08) <= policy.weight_for(L)


def test_noise_profiles_stay_low() -> None:
    # Шум из data.md §5: расплывчатое обращение на «чистого» (N1), единственный производитель
    # (R06 low), аномалия без правил (C6, R08 medium).
    for flags in ([(R.R07, L)], [(R.R06, L)], [(R.R08, M)], [(R.R06, L), (R.R07, L), (R.R08, M)]):
        assert _profile(*flags) <= 40
