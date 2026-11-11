from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.mixins import UUIDMixin
from src.modules.risk.domain.enums import NodeType, RuleCode, Severity
from src.modules.risk.domain.flag import EvidenceNode, RiskFlag
from src.modules.risk.domain.score import RiskScore
from src.modules.risk.infrastructure.database.schema import RISK_SCHEMA


class RiskFlagModel(Base, UUIDMixin):
    __tablename__ = "flags"
    __table_args__ = {"schema": RISK_SCHEMA}

    # Служащий из контекста officials: id без внешнего ключа.
    person_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    rule_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    # [{"type": "person", "id": "...", "label": "..."}, ...] — цепочка узлов графа
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    legal_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_entity(self) -> RiskFlag:
        return RiskFlag(
            id=self.id,
            person_id=self.person_id,
            rule_code=RuleCode(self.rule_code),
            rule_name=self.rule_name,
            severity=Severity(self.severity),
            weight=self.weight,
            explanation=self.explanation,
            evidence=tuple(
                EvidenceNode(type=NodeType(n["type"]), id=UUID(n["id"]), label=n["label"])
                for n in self.evidence
            ),
            legal_ref=self.legal_ref,
            computed_at=self.computed_at,
        )

    @staticmethod
    def row(flag: RiskFlag) -> dict[str, Any]:
        return {
            "id": flag.id,
            "person_id": flag.person_id,
            "rule_code": flag.rule_code.value,
            "rule_name": flag.rule_name,
            "severity": flag.severity.value,
            "weight": flag.weight,
            "explanation": flag.explanation,
            "evidence": [
                {"type": n.type.value, "id": str(n.id), "label": n.label} for n in flag.evidence
            ],
            "legal_ref": flag.legal_ref,
            "computed_at": flag.computed_at,
        }


class RiskScoreModel(Base):
    __tablename__ = "scores"
    __table_args__ = {"schema": RISK_SCHEMA}

    person_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    flags_count: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_entity(self) -> RiskScore:
        return RiskScore(
            person_id=self.person_id,
            score=self.score,
            flags_count=self.flags_count,
            computed_at=self.computed_at,
        )

    @staticmethod
    def row(score: RiskScore) -> dict[str, Any]:
        return {
            "person_id": score.person_id,
            "score": score.score,
            "flags_count": score.flags_count,
            "computed_at": score.computed_at,
        }
