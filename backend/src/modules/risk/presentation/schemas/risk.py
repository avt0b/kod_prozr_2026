from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.core.schemas import APIModel
from src.modules.risk.application.dto.risk_dto import RiskFlagDTO


class EvidenceNodeResponse(BaseModel):
    """Узел цепочки доказательства. node_id совпадает с id узла /officials/{id}/graph."""

    node_id: UUID
    type: str
    label: str


class RiskFlagResponse(APIModel):
    id: UUID
    person_id: UUID
    rule_code: str
    rule_name: str
    severity: str
    weight: float
    explanation: str
    evidence: list[EvidenceNodeResponse]
    legal_ref: str | None
    computed_at: datetime

    @classmethod
    def from_dto(cls, dto: RiskFlagDTO) -> "RiskFlagResponse":
        return cls(
            id=dto.id,
            person_id=dto.person_id,
            rule_code=dto.rule_code,
            rule_name=dto.rule_name,
            severity=dto.severity,
            weight=dto.weight,
            explanation=dto.explanation,
            evidence=[
                EvidenceNodeResponse(node_id=e.id, type=e.type, label=e.label) for e in dto.evidence
            ],
            legal_ref=dto.legal_ref,
            computed_at=dto.computed_at,
        )


class RecomputeResponse(APIModel):
    officials_processed: int
    flags_total: int
    flags_by_rule: dict[str, int]
    computed_at: datetime


class GraphNodeResponse(APIModel):
    id: UUID
    type: str
    label: str
    risk: float | None = None


class GraphEdgeResponse(APIModel):
    source: UUID
    target: UUID
    type: str
    label: str


class GraphResponse(APIModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    truncated: bool = False
