from datetime import datetime
from uuid import UUID

from src.core.schemas import APIModel


class EvidenceNodeResponse(APIModel):
    type: str
    id: UUID
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
