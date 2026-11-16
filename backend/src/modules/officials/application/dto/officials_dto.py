"""DTO слоя application. Наружу из use case уходят они, а не доменные сущности."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True)
class OrganDTO:
    id: UUID
    name: str
    inn: str
    region: str


@dataclass(frozen=True)
class AuthorityDTO:
    id: UUID
    position_id: UUID
    kind: str
    okpd2: tuple[str, ...]
    okved: tuple[str, ...]
    territory: str | None


@dataclass(frozen=True)
class PositionDTO:
    id: UUID
    organ_id: UUID
    title: str
    department: str
    is_corruption_risky: bool


@dataclass(frozen=True)
class PersonDTO:
    id: UUID
    full_name: str
    inn: str | None
    birth_date: date | None
    address: str | None
    phone: str | None


@dataclass(frozen=True)
class AppointmentDTO:
    id: UUID
    person_id: UUID
    started_at: date
    ended_at: date | None
    is_active: bool
    position: PositionDTO
    organ: OrganDTO
    authorities: tuple[AuthorityDTO, ...]


@dataclass(frozen=True)
class RelativeDTO:
    person_id: UUID  # чей это родственник
    kinship_id: UUID
    kind: str
    person: PersonDTO


@dataclass(frozen=True)
class EmploymentDTO:
    id: UUID
    person_id: UUID
    company_id: UUID
    started_at: date
    ended_at: date | None


@dataclass(frozen=True)
class OfficialSnapshotDTO:
    """Всё, что officials знает о служащем. Источник для ACL других модулей (risk, reports)."""

    person: PersonDTO
    appointments: tuple[AppointmentDTO, ...]
    relatives: tuple[RelativeDTO, ...]
    employments: tuple[EmploymentDTO, ...]

    @property
    def current_appointment(self) -> AppointmentDTO | None:
        active = [a for a in self.appointments if a.is_active]
        pool = active or list(self.appointments)
        return max(pool, key=lambda a: a.started_at) if pool else None


@dataclass(frozen=True)
class CompanyView:
    """Компания — приходит из counterparties через ACL."""

    id: UUID
    inn: str
    ogrn: str
    name: str
    okved: str
    address: str | None
    phone: str | None
    registered_at: date | None
    status: str


@dataclass(frozen=True)
class CompanyRoleView:
    """Роль человека в компании (учредитель или директор) — из counterparties через ACL."""

    person_id: UUID
    company: CompanyView
    role: str
    share: float | None
    started_at: date
    ended_at: date | None


@dataclass(frozen=True)
class ContractView:
    supplier_company_id: UUID
    customer_organ_id: UUID
    amount: float
    signed_at: date


@dataclass(frozen=True)
class CompanyLinkDTO:
    """Компания в профиле: связь служащего или родственника, с контрактами органов служащего."""

    company: CompanyView
    role: str  # founder | director | employee
    share: float | None
    via_person_id: UUID
    via_person_name: str
    relation: str  # self | вид родства
    started_at: date
    ended_at: date | None
    contracts_count: int
    contracts_amount: float


@dataclass(frozen=True)
class RiskScoreView:
    score: float
    flags_count: int


@dataclass(frozen=True)
class EvidenceView:
    node_id: UUID
    type: str
    label: str


@dataclass(frozen=True)
class RiskFlagView:
    """Флаг риска — приходит из risk через ACL."""

    id: UUID
    person_id: UUID
    rule_code: str
    rule_name: str
    severity: str
    weight: float
    explanation: str
    evidence: tuple[EvidenceView, ...]
    legal_ref: str | None
    computed_at: datetime


@dataclass(frozen=True)
class OfficialListItemDTO:
    id: UUID
    full_name: str
    position: PositionDTO | None
    organ: OrganDTO | None
    risk_score: float
    top_flags: tuple[RiskFlagView, ...]


@dataclass(frozen=True)
class OfficialRiskDTO:
    score: float
    computed_at: datetime | None
    flags: tuple[RiskFlagView, ...]


@dataclass(frozen=True)
class OfficialProfileDTO:
    person: PersonDTO
    appointments: tuple[AppointmentDTO, ...]
    authorities: tuple[AuthorityDTO, ...]
    relatives: tuple[RelativeDTO, ...]
    companies: tuple[CompanyLinkDTO, ...]
    employments: tuple[EmploymentDTO, ...]
    risk: OfficialRiskDTO
