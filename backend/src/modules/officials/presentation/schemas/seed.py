"""Формат JSON-файлов синтетики для контекста officials (по одному файлу на сущность)."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.officials.domain.appointment import Appointment
from src.modules.officials.domain.enums import AuthorityKind, KinshipKind
from src.modules.officials.domain.organ import Authority, Organ, Position
from src.modules.officials.domain.person import Employment, Kinship, Person
from src.modules.officials.domain.value_objects import AuthorityScope, Period


class OrganSeed(BaseModel):
    id: UUID
    name: str
    inn: str
    region: str

    def to_entity(self) -> Organ:
        return Organ(id=self.id, name=self.name, inn=self.inn, region=self.region)


class PositionSeed(BaseModel):
    id: UUID
    organ_id: UUID
    title: str
    department: str = ""
    is_corruption_risky: bool = False

    def to_entity(self) -> Position:
        return Position(
            id=self.id,
            organ_id=self.organ_id,
            title=self.title,
            department=self.department,
            is_corruption_risky=self.is_corruption_risky,
        )


class AuthorityScopeSeed(BaseModel):
    okpd2: list[str] = Field(default_factory=list)
    okved: list[str] = Field(default_factory=list)
    territory: str | None = None


class AuthoritySeed(BaseModel):
    id: UUID
    position_id: UUID
    kind: AuthorityKind
    scope: AuthorityScopeSeed = Field(default_factory=AuthorityScopeSeed)

    def to_entity(self) -> Authority:
        return Authority(
            id=self.id,
            position_id=self.position_id,
            kind=self.kind,
            scope=AuthorityScope(
                okpd2=tuple(self.scope.okpd2),
                okved=tuple(self.scope.okved),
                territory=self.scope.territory,
            ),
        )


class PersonSeed(BaseModel):
    id: UUID
    full_name: str
    inn: str | None = None
    birth_date: date | None = None
    address: str | None = None
    phone: str | None = None

    def to_entity(self) -> Person:
        return Person(**self.model_dump())


class KinshipSeed(BaseModel):
    id: UUID
    person_id: UUID
    relative_id: UUID
    kind: KinshipKind

    def to_entity(self) -> Kinship:
        return Kinship(**self.model_dump())


class EmploymentSeed(BaseModel):
    id: UUID
    person_id: UUID
    company_id: UUID
    started_at: date
    ended_at: date | None = None

    def to_entity(self) -> Employment:
        return Employment(
            id=self.id,
            person_id=self.person_id,
            company_id=self.company_id,
            period=Period(self.started_at, self.ended_at),
        )


class AppointmentSeed(BaseModel):
    id: UUID
    person_id: UUID
    position_id: UUID
    started_at: date
    ended_at: date | None = None

    def to_entity(self) -> Appointment:
        return Appointment(
            id=self.id,
            person_id=self.person_id,
            position_id=self.position_id,
            period=Period(self.started_at, self.ended_at),
        )
