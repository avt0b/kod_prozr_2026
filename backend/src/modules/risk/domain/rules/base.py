from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import ClassVar

from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import OfficialFacts, PersonFacts
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.score import ScorePolicy
from src.modules.risk.domain.world import RiskWorld


class RiskRule(ABC):
    """Правило риска: чистая функция (служащий, мир) -> флаги.

    Новое правило = подкласс с code/name/severity/legal_ref и методом evaluate,
    плюс строка в DEFAULT_RULES (rules/__init__.py). БД и сеть правилу недоступны —
    всё нужное должно быть в RiskWorld (его наполняет application/services/world_loader.py).
    """

    code: ClassVar[RuleCode]
    name: ClassVar[str]
    severity: ClassVar[Severity]
    legal_ref: ClassVar[str | None] = None

    def __init__(self, policy: ScorePolicy | None = None) -> None:
        self._policy = policy or ScorePolicy()

    @abstractmethod
    def evaluate(self, official: OfficialFacts, world: RiskWorld) -> list[RiskFlag]:
        """Вернуть флаги для служащего. Нет оснований — пустой список."""

    def make_flag(
        self,
        official: OfficialFacts,
        explanation: str,
        evidence: Sequence[EvidenceNode],
        *,
        severity: Severity | None = None,
        weight: float | None = None,
        computed_at: datetime | None = None,
    ) -> RiskFlag:
        level = severity or self.severity
        return RiskFlag(
            person_id=official.person.id,
            rule_code=self.code,
            rule_name=self.name,
            severity=level,
            weight=self._policy.weight_for(level) if weight is None else weight,
            explanation=explanation,
            evidence=tuple(evidence),
            legal_ref=self.legal_ref,
            computed_at=computed_at or datetime.now(UTC),
        )


def person_node(person: PersonFacts) -> EvidenceNode:
    return EvidenceNode(type=NodeType.PERSON, id=person.id, label=person.full_name)


def quoted(name: str) -> str:
    """ООО «Ромашка» остаётся как есть, «Администрация» без кавычек -> «Администрация»."""
    return name if "«" in name or '"' in name else f"«{name}»"
