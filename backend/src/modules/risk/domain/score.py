from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.modules.risk.domain.enums import Severity
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


@dataclass(frozen=True)
class ScorePolicy:
    """Веса уровней и нормирование балла — единственное место, где они заданы.

    Контракт: «итоговый балл = сумма весов флагов, нормированная в 0–100».
    Нормирование: обрезка сверху до 100 (два high-флага + medium = 100).
    """

    high: float = 40.0
    medium: float = 20.0
    low: float = 10.0

    def weight_for(self, severity: Severity) -> float:
        return {Severity.HIGH: self.high, Severity.MEDIUM: self.medium, Severity.LOW: self.low}[
            severity
        ]

    def score(self, person_id: UUID, flags: Sequence[RiskFlag], computed_at: datetime) -> RiskScore:
        total = sum(flag.weight for flag in flags)
        return RiskScore(
            person_id=person_id,
            score=round(min(MAX_SCORE, total), 1),
            flags_count=len(flags),
            computed_at=computed_at,
        )
