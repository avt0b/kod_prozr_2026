"""Сводка риска по группе служащих (должность или орган) для карты рисков."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

TOP_RULES = 5
TOP_OFFICIALS = 3


@dataclass(frozen=True)
class OfficialRisk:
    """Служащий в группе: балл и коды правил его флагов."""

    person_id: UUID
    full_name: str
    score: float
    rule_codes: tuple[str, ...]

    @property
    def is_flagged(self) -> bool:
        return bool(self.rule_codes)


@dataclass(frozen=True)
class RuleCount:
    rule_code: str
    count: int  # число служащих группы с флагом этого правила


@dataclass(frozen=True)
class RiskAggregate:
    officials_total: int
    officials_with_flags: int
    flagged_share: float  # 0–1
    avg_score: float
    max_score: float
    top_rules: tuple[RuleCount, ...]
    top_officials: tuple[OfficialRisk, ...]

    @classmethod
    def of(cls, officials: Sequence[OfficialRisk]) -> "RiskAggregate":
        total = len(officials)
        flagged = sum(1 for o in officials if o.is_flagged)
        scores = [o.score for o in officials]
        rules = Counter(code for o in officials for code in set(o.rule_codes))
        # Частые правила: по числу служащих, при равенстве — по коду.
        top_rules = sorted(rules.items(), key=lambda item: (-item[1], item[0]))[:TOP_RULES]
        # Топ служащих: только с флагами, по баллу, затем по ФИО (стабильный порядок).
        ranked = sorted(
            (o for o in officials if o.is_flagged), key=lambda o: (-o.score, o.full_name)
        )
        return cls(
            officials_total=total,
            officials_with_flags=flagged,
            flagged_share=round(flagged / total, 3) if total else 0.0,
            avg_score=round(sum(scores) / total, 1) if total else 0.0,
            max_score=max(scores, default=0.0),
            top_rules=tuple(RuleCount(code, count) for code, count in top_rules),
            top_officials=tuple(ranked[:TOP_OFFICIALS]),
        )
