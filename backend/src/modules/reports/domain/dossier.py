from dataclasses import dataclass, field
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class FlagSummary:
    rule_code: str
    rule_name: str
    severity: str
    explanation: str
    legal_ref: str | None
    evidence: tuple[str, ...] = ()  # подписи узлов цепочки: «Иванов И.И.» -> «ООО ...» -> ...


@dataclass(frozen=True)
class AppealSummary:
    appeal_id: UUID
    received_at: str
    summary: str
    specificity: float


@dataclass(frozen=True)
class Dossier:
    """Всё, что нужно для докладной: кто, где служит, какой риск и почему.

    Собирается из officials и risk через ACL — reports не знает их моделей.
    """

    person_id: UUID
    full_name: str
    position_title: str | None
    department: str | None
    organ_name: str | None
    appointed_at: date | None
    score: float
    flags: tuple[FlagSummary, ...] = field(default_factory=tuple)

    authorities: tuple[str, ...] = ()
    appeals: tuple[AppealSummary, ...] = ()
    ended_at: date | None = None

    @property
    def has_flags(self) -> bool:
        return bool(self.flags)
