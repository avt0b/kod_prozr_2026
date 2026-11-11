from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from src.modules.counterparties.domain.enums import CompanyRoleKind, CompanyStatus
from src.modules.counterparties.domain.exceptions import InvalidRolePeriodError, InvalidShareError


@dataclass
class Company:
    """Юрлицо — потенциальный контрагент органа."""

    inn: str
    ogrn: str
    name: str
    okved: str
    address: str | None = None
    phone: str | None = None
    registered_at: date | None = None
    status: CompanyStatus = CompanyStatus.ACTIVE
    id: UUID = field(default_factory=uuid4)

    @property
    def is_active(self) -> bool:
        return self.status is CompanyStatus.ACTIVE


@dataclass
class CompanyRole:
    """Учредитель или руководитель компании. person_id — из контекста officials, без FK."""

    company_id: UUID
    person_id: UUID
    role: CompanyRoleKind
    started_at: date
    ended_at: date | None = None
    share: float | None = None  # доля в уставном капитале, %
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.share is not None and not 0 <= self.share <= 100:
            raise InvalidShareError()
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise InvalidRolePeriodError()

    def is_active_on(self, day: date) -> bool:
        return self.started_at <= day and (self.ended_at is None or day <= self.ended_at)
