from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import UUID

from src.modules.risk.domain.enums import RuleCode, Severity
from src.modules.risk.domain.flag import RiskFlag

MAX_SCORE = 100.0


@dataclass(frozen=True)
class RiskScore:
    person_id: UUID
    score: float
    flags_count: int
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not 0 <= self.score <= MAX_SCORE:
            raise ValueError("score must be within 0..100")


_ML_WEIGHTS: Mapping[Severity, float] = MappingProxyType(
    {Severity.LOW: 5.0, Severity.MEDIUM: 10.0, Severity.HIGH: 10.0}
)


@dataclass(frozen=True)
class ScorePolicy:
    """Методика балла (ADR-04, docs/backend.md) — единственное место, где заданы веса.

    Вес флага: high 40, medium 20, low 7. R08 (ML) весит 5 (low) или 10 (medium и выше):
    ML в одиночку не выводит служащего в топ.

    Балл: score = min(100, Σ вклад правил).
      Вклад правила = вес его самого тяжёлого флага + половина веса каждого следующего флага
      того же правила, но не больше двух весов самого тяжёлого флага. Так десять однотипных
      связей не перевешивают две разные схемы.

    Веса предварительные: при калибровке (B-17) меняем только константы и тест эталонных случаев.
    """

    high: float = 40.0
    medium: float = 20.0
    low: float = 7.0
    ml_weights: Mapping[Severity, float] = field(default_factory=lambda: _ML_WEIGHTS)
    repeat_factor: float = 0.5
    rule_cap_factor: float = 2.0

    def weight_for(self, severity: Severity, rule_code: RuleCode | None = None) -> float:
        if rule_code is RuleCode.R08:
            return self.ml_weights[severity]
        return {Severity.HIGH: self.high, Severity.MEDIUM: self.medium, Severity.LOW: self.low}[
            severity
        ]

    def rule_contribution(self, weights: Sequence[float]) -> float:
        if not weights:
            return 0.0
        ordered = sorted(weights, reverse=True)
        top = ordered[0]
        total = top + self.repeat_factor * sum(ordered[1:])
        return min(total, self.rule_cap_factor * top)

    def score(self, person_id: UUID, flags: Sequence[RiskFlag], computed_at: datetime) -> RiskScore:
        by_rule: dict[RuleCode, list[float]] = defaultdict(list)
        for flag in flags:
            by_rule[flag.rule_code].append(flag.weight)
        total = sum(self.rule_contribution(weights) for weights in by_rule.values())
        return RiskScore(
            person_id=person_id,
            score=round(min(MAX_SCORE, total), 1),
            flags_count=len(flags),
            computed_at=computed_at,
        )
