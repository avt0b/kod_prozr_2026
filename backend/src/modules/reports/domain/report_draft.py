from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.reports.domain.exceptions import EmptyReportTextError

# ADR-09: человек в контуре. Дисклеймер есть в каждом черновике, независимо от генератора.
DISCLAIMER = (
    "Черновик сформирован автоматически по данным информационной системы и не является "
    "выводом о нарушении. Выявленные признаки требуют проверки уполномоченным должностным "
    "лицом; решение принимает человек."
)


@dataclass
class ReportDraft:
    """Черновик докладной записки по служащему."""

    person_id: UUID
    text: str
    generator: str = "template"  # template / llm:<model>
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise EmptyReportTextError()
        if DISCLAIMER not in self.text:
            self.text = f"{self.text.rstrip()}\n\n{DISCLAIMER}"
