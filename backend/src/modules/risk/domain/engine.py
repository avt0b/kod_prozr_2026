from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID

from src.modules.risk.domain.enums import NodeType
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.graph import contract_group_id
from src.modules.risk.domain.rules.base import RiskRule
from src.modules.risk.domain.score import RiskScore, ScorePolicy
from src.modules.risk.domain.world import RiskWorld


@dataclass(frozen=True)
class RiskAssessment:
    flags: list[RiskFlag]
    scores: list[RiskScore]
    computed_at: datetime


class RiskEngine:
    """Доменный сервис: прогоняет правила по всем служащим мира и считает баллы."""

    def __init__(self, rules: list[RiskRule], policy: ScorePolicy | None = None) -> None:
        self._rules = rules
        self._policy = policy or ScorePolicy()

    def assess(
        self,
        world: RiskWorld,
        computed_at: datetime | None = None,
        carried_flags: Sequence[RiskFlag] = (),
    ) -> RiskAssessment:
        """carried_flags — флаги прошлого расчёта, которые нельзя пересчитать на этом снимке
        (R08 при частичном пересчёте): они входят в балл как есть."""
        computed_at = computed_at or datetime.now(UTC)
        carried: dict[UUID, list[RiskFlag]] = defaultdict(list)
        for flag in carried_flags:
            carried[flag.person_id].append(flag)
        all_flags: list[RiskFlag] = []
        scores: list[RiskScore] = []
        for official in world.officials.values():
            flags = [
                replace(flag, computed_at=computed_at)
                for rule in self._rules
                for flag in rule.evaluate(official, world)
            ]
            flags += [replace(f, computed_at=computed_at) for f in carried[official.person.id]]
            flags = [_group_contract_evidence(flag, world) for flag in flags]
            all_flags.extend(flags)
            scores.append(self._policy.score(official.person.id, flags, computed_at))
        return RiskAssessment(flags=all_flags, scores=scores, computed_at=computed_at)


def _group_contract_evidence(flag: RiskFlag, world: RiskWorld) -> RiskFlag:
    """Keep every rule's facts while sharing contract node identities with the graph."""
    nodes: dict[UUID, EvidenceNode] = {}
    for node in flag.evidence:
        contract = world.contracts_by_id.get(node.id) if node.type is NodeType.CONTRACT else None
        if contract:
            node = replace(
                node, id=contract_group_id(contract.supplier_company_id, contract.customer_organ_id)
            )
        previous = nodes.get(node.id)
        if previous and previous.label != node.label:
            node = replace(node, label=previous.label + "; " + node.label)
        nodes[node.id] = node
    return replace(flag, evidence=tuple(nodes.values()))
