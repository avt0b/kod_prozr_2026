from datetime import date

import pytest

from src.modules.risk.domain.enums import NodeType, Severity
from src.modules.risk.domain.facts import AppealMentionFacts
from src.modules.risk.domain.rules.r07_appeal_mentions import AppealMentionsRule
from src.modules.risk.domain.world import RiskWorld
from tests.unit.risk.conftest import make_official, uid


def _mention(key: str, *, confidence: float, specificity: float, corrupt: bool = True) -> AppealMentionFacts:
    return AppealMentionFacts(
        appeal_id=uid(key),
        person_id=uid("official"),
        is_corruption=corrupt,
        category="bribe",
        specificity=specificity,
        confidence=confidence,
        received_at=date(2026, 10, 1),
    )


@pytest.mark.parametrize(
    ("mentions", "expected"),
    [
        ([("a1", 0.6, 0.5)], Severity.LOW),  # s = 0.30: одно расплывчатое — только low
        ([("a1", 0.9, 0.9)], Severity.MEDIUM),  # s = 0.81
        ([("a1", 0.9, 0.9), ("a2", 0.9, 0.9)], Severity.HIGH),  # s = 1.62
    ],
)
def test_r07_severity_follows_ai_md_formula(
    today: date, mentions: list[tuple[str, float, float]], expected: Severity
) -> None:
    official = make_official()
    world = RiskWorld(
        today=today,
        officials=[official],
        appeal_mentions=[_mention(k, confidence=c, specificity=s) for k, c, s in mentions],
    )

    flags = AppealMentionsRule().evaluate(official, world)

    assert len(flags) == 1
    assert flags[0].severity is expected
    assert [n.type for n in flags[0].evidence[1:]] == [NodeType.APPEAL] * len(mentions)


def test_r07_ignores_appeals_without_corruption(today: date) -> None:
    official = make_official()
    world = RiskWorld(
        today=today,
        officials=[official],
        appeal_mentions=[_mention("a1", confidence=0.9, specificity=0.9, corrupt=False)],
    )

    assert AppealMentionsRule().evaluate(official, world) == []
