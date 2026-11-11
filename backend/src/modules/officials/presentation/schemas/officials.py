from datetime import date
from uuid import UUID

from pydantic import BaseModel

from src.core.schemas import APIModel
from src.modules.officials.application.dto.officials_dto import AuthorityDTO


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


class RiskFlagBriefResponse(APIModel):
    id: UUID
    rule_code: str
    rule_name: str
    severity: str
    weight: float
    explanation: str
    legal_ref: str | None


class OfficialListItemResponse(APIModel):
    id: UUID
    full_name: str
    position: PositionResponse | None
    organ: OrganResponse | None
    risk_score: float
    top_flags: list[RiskFlagBriefResponse]


class AppointmentResponse(BaseModel):
    id: UUID
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


class CompanyLinkResponse(APIModel):
    person_id: UUID
    company_id: UUID
    company_name: str
    company_inn: str
    company_status: str
    role: str
    share: float | None
    started_at: date
    ended_at: date | None


class EmploymentResponse(APIModel):
    id: UUID
    company_id: UUID
    started_at: date
    ended_at: date | None


class OfficialRiskResponse(APIModel):
    score: float
    flags: list[RiskFlagBriefResponse]


class OfficialProfileResponse(BaseModel):
    person: PersonResponse
    appointments: list[AppointmentResponse]
    authorities: list[AuthorityResponse]
    relatives: list[RelativeResponse]
    companies: list[CompanyLinkResponse]
    employments: list[EmploymentResponse]
    risk: OfficialRiskResponse
