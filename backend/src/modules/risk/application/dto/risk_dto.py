from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.graph import ConnectionsGraph
from src.modules.risk.domain.score import RiskScore


@dataclass(frozen=True)
class EvidenceNodeDTO:
    type: str
    id: UUID
    label: str


@dataclass(frozen=True)
class RiskFlagDTO:
    id: UUID
    person_id: UUID
    rule_code: str
    rule_name: str
    severity: str
    weight: float
    explanation: str
    evidence: tuple[EvidenceNodeDTO, ...]
    legal_ref: str | None
    computed_at: datetime

    @classmethod
    def from_entity(cls, flag: RiskFlag) -> "RiskFlagDTO":
        return cls(
            id=flag.id,
            person_id=flag.person_id,
            rule_code=flag.rule_code.value,
            rule_name=flag.rule_name,
            severity=flag.severity.value,
            weight=flag.weight,
            explanation=flag.explanation,
            evidence=tuple(
                EvidenceNodeDTO(type=n.type.value, id=n.id, label=n.label) for n in flag.evidence
            ),
            legal_ref=flag.legal_ref,
            computed_at=flag.computed_at,
        )


@dataclass(frozen=True)
class RiskScoreDTO:
    person_id: UUID
    score: float
    flags_count: int
    computed_at: datetime

    @classmethod
    def from_entity(cls, score: RiskScore) -> "RiskScoreDTO":
        return cls(
            person_id=score.person_id,
            score=score.score,
            flags_count=score.flags_count,
            computed_at=score.computed_at,
        )


@dataclass(frozen=True)
class RecomputeResultDTO:
    officials_processed: int
    flags_total: int
    flags_by_rule: dict[str, int]
    computed_at: datetime


@dataclass(frozen=True)
class GraphNodeDTO:
    id: UUID
    type: str
    label: str
    risk: float | None


@dataclass(frozen=True)
class GraphEdgeDTO:
    source: UUID
    target: UUID
    type: str
    label: str


@dataclass(frozen=True)
class GraphDTO:
    nodes: list[GraphNodeDTO]
    edges: list[GraphEdgeDTO]
    truncated: bool = False

    @classmethod
    def from_graph(cls, graph: ConnectionsGraph) -> "GraphDTO":
        return cls(
            nodes=[GraphNodeDTO(n.id, n.type.value, n.label, n.risk) for n in graph.nodes],
            edges=[GraphEdgeDTO(e.source, e.target, e.type.value, e.label) for e in graph.edges],
            truncated=graph.truncated,
        )


@dataclass(frozen=True)
class RiskStatsDTO:
    flags_by_severity: dict[str, int] = field(default_factory=dict)
    flagged_officials: int = 0
    computed_at: datetime | None = None
