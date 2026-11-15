from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from src.core.schemas import APIModel
from src.modules.stats.application.use_cases.get_risk_map import (
    OrganRiskDTO,
    PositionRiskDTO,
    RiskMapDTO,
)
from src.modules.stats.domain.risk_map import RiskAggregate


class TypicalRiskResponse(APIModel):
    code: str
    title: str
    description: str
    authority: str
    rule_codes: list[str]  # правила R01–R08, которыми система ищет этот риск
    legal_ref: str


class RuleCountResponse(APIModel):
    rule_code: str
    count: int  # служащих с флагом этого правила


class TopOfficialResponse(APIModel):
    id: UUID
    full_name: str
    risk_score: float


class _AggregateResponse(APIModel):
    officials_total: int
    officials_with_flags: int
    flagged_share: float  # 0–1
    avg_score: float
    max_score: float
    top_rules: list[RuleCountResponse]
    top_officials: list[TopOfficialResponse]


def _aggregate(stats: RiskAggregate) -> dict[str, Any]:
    return {
        "officials_total": stats.officials_total,
        "officials_with_flags": stats.officials_with_flags,
        "flagged_share": stats.flagged_share,
        "avg_score": stats.avg_score,
        "max_score": stats.max_score,
        "top_rules": [RuleCountResponse.model_validate(r) for r in stats.top_rules],
        "top_officials": [
            TopOfficialResponse(id=o.person_id, full_name=o.full_name, risk_score=o.score)
            for o in stats.top_officials
        ],
    }


class PositionRiskResponse(_AggregateResponse):
    position_id: UUID
    title: str
    department: str
    organ_id: UUID
    organ: str
    is_corruption_risky: bool
    authorities: list[str]
    risk_level: Literal["high", "medium", "low"]  # риск должности по полномочиям (вариант D)
    typical_risks: list[TypicalRiskResponse]

    @classmethod
    def from_dto(cls, dto: PositionRiskDTO) -> "PositionRiskResponse":
        return cls.model_validate(
            {
                "position_id": dto.position_id,
                "title": dto.title,
                "department": dto.department,
                "organ_id": dto.organ_id,
                "organ": dto.organ,
                "is_corruption_risky": dto.is_corruption_risky,
                "authorities": list(dto.authorities),
                "risk_level": dto.risk_level,
                "typical_risks": [TypicalRiskResponse.model_validate(r) for r in dto.typical_risks],
                **_aggregate(dto.stats),
            }
        )


class OrganRiskResponse(_AggregateResponse):
    organ_id: UUID
    organ: str
    positions_total: int

    @classmethod
    def from_dto(cls, dto: OrganRiskDTO) -> "OrganRiskResponse":
        return cls.model_validate(
            {
                "organ_id": dto.organ_id,
                "organ": dto.organ,
                "positions_total": dto.positions_total,
                **_aggregate(dto.stats),
            }
        )


class RiskMapResponse(APIModel):
    items: list[PositionRiskResponse]
    total: int
    organs: list[OrganRiskResponse]
    computed_at: datetime | None  # последний пересчёт риска

    @classmethod
    def from_dto(cls, dto: RiskMapDTO) -> "RiskMapResponse":
        return cls(
            items=[PositionRiskResponse.from_dto(i) for i in dto.items],
            total=dto.total,
            organs=[OrganRiskResponse.from_dto(o) for o in dto.organs],
            computed_at=dto.computed_at,
        )
