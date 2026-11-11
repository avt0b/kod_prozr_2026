from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from src.modules.officials.domain.enums import KinshipKind
from src.modules.officials.domain.exceptions import SelfKinshipError
from src.modules.officials.domain.value_objects import Period


@dataclass
class Person:
    """Физическое лицо. «Служащий» = Person, у которого есть хотя бы одно Appointment."""

    full_name: str
    inn: str | None = None
    birth_date: date | None = None
    address: str | None = None
    phone: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class Kinship:
    """Родство: relative_id — родственник person_id, kind — кем он ему приходится."""

    person_id: UUID
    relative_id: UUID
    kind: KinshipKind
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.person_id == self.relative_id:
            raise SelfKinshipError()

    def relative_of(self, person_id: UUID) -> tuple[UUID, KinshipKind] | None:
        """Родственник для person_id и степень родства с его точки зрения.

        Родство хранится одной записью, а читается с обеих сторон.
        """
        if person_id == self.person_id:
            return self.relative_id, self.kind
        if person_id == self.relative_id:
            return self.person_id, self.kind.inverse()
        return None


@dataclass
class Employment:
    """Прошлое (или текущее) место работы вне госслужбы."""

    person_id: UUID
    company_id: UUID  # id компании из контекста counterparties, без FK
    period: Period
    id: UUID = field(default_factory=uuid4)
