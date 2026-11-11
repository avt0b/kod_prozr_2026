from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import ClassVar
from uuid import UUID

from src.core.utils.text import format_rub
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.facts import CompanyFacts, ContractFacts, OfficialFacts, PersonFacts
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
            weight=self._policy.weight_for(level, self.code) if weight is None else weight,
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


MAX_EVIDENCE_CONTRACTS = 5


def company_node(company: CompanyFacts) -> EvidenceNode:
    return EvidenceNode(type=NodeType.COMPANY, id=company.id, label=company.name)


def organ_node(organ_id: UUID, organ_name: str) -> EvidenceNode:
    return EvidenceNode(type=NodeType.ORGAN, id=organ_id, label=organ_name)


def contract_nodes(contracts: Sequence[ContractFacts]) -> list[EvidenceNode]:
    """Первые MAX_EVIDENCE_CONTRACTS контрактов по дате: цепочка не разрастается."""
    ordered = sorted(contracts, key=lambda c: c.signed_at)[:MAX_EVIDENCE_CONTRACTS]
    return [
        EvidenceNode(
            type=NodeType.CONTRACT,
            id=c.id,
            label=f"№{c.reg_number} от {c.signed_at:%d.%m.%Y}, {format_rub(c.amount)}",
        )
        for c in ordered
    ]


def plural_contracts(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "контракт"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "контракта"
    return "контрактов"


def contracts_summary(contracts: Sequence[ContractFacts]) -> str:
    """«3 контракта на 12,5 млн руб.»"""
    total = sum(c.amount for c in contracts)
    return f"{len(contracts)} {plural_contracts(len(contracts))} на {format_rub(total)}"


def years_between(start: date, end: date) -> float:
    return (end - start).days / 365.25
