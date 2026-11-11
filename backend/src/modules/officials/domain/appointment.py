from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from src.modules.officials.domain.value_objects import Period


@dataclass
class Appointment:
    """Замещение должности: человек занимал position_id в течение period."""

    person_id: UUID
    position_id: UUID
    period: Period
    id: UUID = field(default_factory=uuid4)

    def is_active(self, today: date) -> bool:
        return self.period.is_active(today)
