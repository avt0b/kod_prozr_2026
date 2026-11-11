from dataclasses import dataclass, field

from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.core.infrastructure.logger import get_logger
from src.modules.officials.application.interfaces.appointment_repository import (
    AppointmentRepositoryInterface,
)
from src.modules.officials.application.interfaces.organ_repository import (
    OrganRepositoryInterface,
)
from src.modules.officials.application.interfaces.person_repository import (
    PersonRepositoryInterface,
)
from src.modules.officials.domain.appointment import Appointment
from src.modules.officials.domain.organ import Authority, Organ, Position
from src.modules.officials.domain.person import Employment, Kinship, Person

logger = get_logger(__name__)


@dataclass
class OfficialsImport:
    organs: list[Organ] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    authorities: list[Authority] = field(default_factory=list)
    persons: list[Person] = field(default_factory=list)
    kinships: list[Kinship] = field(default_factory=list)
    employments: list[Employment] = field(default_factory=list)
    appointments: list[Appointment] = field(default_factory=list)


class ImportOfficialsDataUseCase:
    """Загрузка синтетики/выгрузок (seed). Идемпотентна: upsert по id."""

    def __init__(
        self,
        organ_repository: OrganRepositoryInterface,
        person_repository: PersonRepositoryInterface,
        appointment_repository: AppointmentRepositoryInterface,
        unit_of_work: UnitOfWorkInterface,
    ) -> None:
        self._organs = organ_repository
        self._persons = person_repository
        self._appointments = appointment_repository
        self._unit_of_work = unit_of_work

    async def execute(self, data: OfficialsImport) -> dict[str, int]:
        async with self._unit_of_work:
            await self._organs.upsert_many(data.organs, data.positions, data.authorities)
            await self._persons.upsert_many(data.persons, data.kinships, data.employments)
            await self._appointments.upsert_many(data.appointments)
            await self._unit_of_work.commit()

        counts = {
            "organs": len(data.organs),
            "positions": len(data.positions),
            "authorities": len(data.authorities),
            "persons": len(data.persons),
            "kinships": len(data.kinships),
            "employments": len(data.employments),
            "appointments": len(data.appointments),
        }
        logger.info("Officials data imported: {}", counts)
        return counts
