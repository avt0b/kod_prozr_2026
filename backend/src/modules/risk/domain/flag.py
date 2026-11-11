from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.risk.domain.enums import NodeType, RuleCode, Severity


@dataclass(frozen=True)
class EvidenceNode:
    """Узел цепочки доказательства. type/id совпадают с узлами графа связей."""

    type: NodeType
    id: UUID
    label: str


@dataclass(frozen=True)
class RiskFlag:
    """Сработавшее правило риска. Без объяснения и цепочки доказательств флаг не существует."""

    person_id: UUID
    rule_code: RuleCode
    rule_name: str
    severity: Severity
    weight: float
    explanation: str
    evidence: tuple[EvidenceNode, ...]
    legal_ref: str | None = None
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.explanation.strip():
            raise ValueError("RiskFlag must have an explanation")
        if not self.evidence:
            raise ValueError("RiskFlag must have evidence")
        if self.weight < 0:
            raise ValueError("RiskFlag weight must be non-negative")
