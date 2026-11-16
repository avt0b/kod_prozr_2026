from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from src.core.schemas import APIModel
from src.modules.officials.application.dto.officials_dto import AuthorityDTO, OfficialListItemDTO


class OrganResponse(APIModel):
    id: UUID
    name: str
    inn: str
    region: str


class PositionResponse(APIModel):
    id: UUID
    organ_id: UUID
    title: str
    department: str
    is_corruption_risky: bool


class AuthorityScopeResponse(BaseModel):
    okpd2: list[str]
    okved: list[str]
    territory: str | None


class AuthorityResponse(BaseModel):
    id: UUID
    position_id: UUID
    kind: str
    scope: AuthorityScopeResponse

    @classmethod
    def from_dto(cls, dto: AuthorityDTO) -> "AuthorityResponse":
        return cls(
            id=dto.id,
            position_id=dto.position_id,
            kind=dto.kind,
            scope=AuthorityScopeResponse(
                okpd2=list(dto.okpd2), okved=list(dto.okved), territory=dto.territory
            ),
        )


class PersonResponse(APIModel):
    id: UUID
    full_name: str
    inn: str | None
    birth_date: date | None
    address: str | None
    phone: str | None


class EvidenceResponse(APIModel):
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
    evidence: list[EvidenceResponse]
    legal_ref: str | None
    computed_at: datetime


class FlagShortResponse(BaseModel):
    rule_code: str
    rule_name: str
    severity: str


class OfficialListItemResponse(BaseModel):
    """Элемент рейтинга (contracts.md): position и organ — названия текущей должности и органа."""

    id: UUID
    full_name: str
    position: str | None
    organ: str | None
    organ_id: UUID | None
    risk_score: float
    top_flags: list[FlagShortResponse]

    @classmethod
    def from_dto(cls, dto: OfficialListItemDTO) -> "OfficialListItemResponse":
        return cls(
            id=dto.id,
            full_name=dto.full_name,
            position=dto.position.title if dto.position else None,
            organ=dto.organ.name if dto.organ else None,
            organ_id=dto.organ.id if dto.organ else None,
            risk_score=dto.risk_score,
            top_flags=[
                FlagShortResponse(rule_code=f.rule_code, rule_name=f.rule_name, severity=f.severity)
                for f in dto.top_flags
            ],
        )


class AppointmentResponse(BaseModel):
    id: UUID
    person_id: UUID
    position_id: UUID
    started_at: date
    ended_at: date | None
    is_active: bool
    position: PositionResponse
    organ: OrganResponse
    authorities: list[AuthorityResponse]


class RelativeResponse(APIModel):
    kinship_id: UUID
    kind: str
    person: PersonResponse


class CompanyResponse(APIModel):
    id: UUID
    inn: str
    ogrn: str
    name: str
    okved: str
    address: str | None
    phone: str | None
    registered_at: date | None
    status: str


class CompanyLinkResponse(APIModel):
    company: CompanyResponse
    role: str
    share: float | None
    via_person_id: UUID
    via_person_name: str
    relation: str
    started_at: date
    ended_at: date | None
    contracts_count: int
    contracts_amount: float


class EmploymentResponse(APIModel):
    id: UUID
    company_id: UUID
    started_at: date
    ended_at: date | None


class OfficialRiskResponse(APIModel):
    score: float
    computed_at: datetime | None
    flags: list[RiskFlagResponse]


class OfficialProfileResponse(BaseModel):
    person: PersonResponse
    appointments: list[AppointmentResponse]
    authorities: list[AuthorityResponse]
    relatives: list[RelativeResponse]
    companies: list[CompanyLinkResponse]
    employments: list[EmploymentResponse]
    risk: OfficialRiskResponse
