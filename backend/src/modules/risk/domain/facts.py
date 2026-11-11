"""Модель мира глазами контекста risk.

Это НЕ сущности officials/counterparties/appeals: risk описывает ровно те факты, которые
нужны правилам, своими словами. Наполняют их ACL-адаптеры (infrastructure/adapters).
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

PROCUREMENT = "procurement"

KINSHIP_LABELS = {
    "spouse": "супруг(а)",
    "child": "ребёнок",
    "parent": "родитель",
    "sibling": "брат/сестра",
    "in_law": "свойственник",
    "other": "родственник",
}

ROLE_LABELS = {"founder": "учредитель", "director": "руководитель"}


@dataclass(frozen=True)
class PersonFacts:
    id: UUID
    full_name: str
    address: str | None = None
    phone: str | None = None


@dataclass(frozen=True)
class AuthorityFacts:
    kind: str
    okpd2: tuple[str, ...] = ()

    def covers_okpd2(self, code: str | None) -> bool:
        if not self.okpd2 or code is None:
            return True
        return any(code.startswith(prefix) for prefix in self.okpd2)


@dataclass(frozen=True)
class AppointmentFacts:
    organ_id: UUID
    organ_name: str
    position_title: str
    started_at: date
    ended_at: date | None = None
    authorities: tuple[AuthorityFacts, ...] = ()

    def contains(self, day: date) -> bool:
        return self.started_at <= day and (self.ended_at is None or day <= self.ended_at)

    def authorities_of(self, kind: str) -> tuple[AuthorityFacts, ...]:
        return tuple(a for a in self.authorities if a.kind == kind)


@dataclass(frozen=True)
class RelativeFacts:
    person: PersonFacts
    kind: str

    @property
    def kind_label(self) -> str:
        return KINSHIP_LABELS.get(self.kind, "родственник")


@dataclass(frozen=True)
class EmploymentFacts:
    company_id: UUID
    started_at: date
    ended_at: date | None = None


@dataclass(frozen=True)
class OfficialFacts:
    person: PersonFacts
    appointments: tuple[AppointmentFacts, ...] = ()
    relatives: tuple[RelativeFacts, ...] = ()
    employments: tuple[EmploymentFacts, ...] = ()

    def active_appointments(self, today: date) -> tuple[AppointmentFacts, ...]:
        return tuple(a for a in self.appointments if a.contains(today))


@dataclass(frozen=True)
class OrganFacts:
    id: UUID
    name: str


@dataclass(frozen=True)
class CompanyFacts:
    id: UUID
    name: str
    inn: str
    status: str
    okved: str | None = None
    address: str | None = None
    phone: str | None = None

    @property
    def is_active(self) -> bool:
        return self.status == "active"


@dataclass(frozen=True)
class CompanyRoleFacts:
    company_id: UUID
    person_id: UUID
    role: str
    started_at: date
    ended_at: date | None = None
    share: float | None = None

    def active_on(self, day: date) -> bool:
        return self.started_at <= day and (self.ended_at is None or day <= self.ended_at)

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role)


@dataclass(frozen=True)
class ContractFacts:
    id: UUID
    reg_number: str
    customer_organ_id: UUID
    supplier_company_id: UUID
    amount: float
    signed_at: date
    okpd2: str | None = None


@dataclass(frozen=True)
class AppealMentionFacts:
    appeal_id: UUID
    person_id: UUID
    is_corruption: bool
    category: str | None
    specificity: float
    received_at: date
    confidence: float = 1.0
    summary: str | None = None


@dataclass(frozen=True)
class RelativeLinkFacts:
    """Родство с точки зрения person_id (для обхода графа)."""

    person_id: UUID
    relative: PersonFacts
    kind: str
