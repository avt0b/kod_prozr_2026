from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from uuid import UUID

from src.modules.officials.application.dto.mappers import (
    to_appointment_dto,
    to_employment_dto,
    to_person_dto,
    to_relative_dtos,
)
from src.modules.officials.application.dto.officials_dto import OfficialSnapshotDTO
from src.modules.officials.application.interfaces.appointment_repository import (
    AppointmentRepositoryInterface,
)
from src.modules.officials.application.interfaces.organ_repository import (
    OrganRepositoryInterface,
)
from src.modules.officials.application.interfaces.person_repository import (
    PersonRepositoryInterface,
)
from src.modules.officials.domain.organ import Authority


class GetOfficialSnapshotsUseCase:
    """Собирает «снимок» служащих пачкой: человек, назначения с должностью/органом/полномочиями,
    родственники, прошлые места работы. Число запросов не зависит от числа служащих.

    Используется профилем и ACL-адаптерами других модулей (risk, reports).
    Люди без назначений (не служащие) в результат не попадают.
    """

    def __init__(
        self,
        person_repository: PersonRepositoryInterface,
        appointment_repository: AppointmentRepositoryInterface,
        organ_repository: OrganRepositoryInterface,
    ) -> None:
        self._persons = person_repository
        self._appointments = appointment_repository
        self._organs = organ_repository

    async def execute(
        self, person_ids: Sequence[UUID], today: date | None = None
    ) -> list[OfficialSnapshotDTO]:
        today = today or date.today()
        if not person_ids:
            return []

        appointments = await self._appointments.list_for_persons(person_ids)
        official_ids = list(dict.fromkeys(a.person_id for a in appointments))
        if not official_ids:
            return []

        positions = {
            p.id: p
            for p in await self._organs.get_positions(list({a.position_id for a in appointments}))
        }
        organs = {
            o.id: o
            for o in await self._organs.get_many(list({p.organ_id for p in positions.values()}))
        }
        authorities_by_position: dict[UUID, list[Authority]] = defaultdict(list)
        for authority in await self._organs.get_authorities(list(positions)):
            authorities_by_position[authority.position_id].append(authority)

        kinships = await self._persons.get_kinships(official_ids)
        related_ids = {k.person_id for k in kinships} | {k.relative_id for k in kinships}
        persons = {
            p.id: p for p in await self._persons.get_many(list(related_ids | set(official_ids)))
        }
        employments = await self._persons.get_employments(official_ids)

        snapshots: list[OfficialSnapshotDTO] = []
        for person_id in official_ids:
            person = persons.get(person_id)
            if person is None:
                continue
            own_appointments = []
            for appointment in appointments:
                if appointment.person_id != person_id:
                    continue
                position = positions.get(appointment.position_id)
                organ = organs.get(position.organ_id) if position else None
                if position is None or organ is None:
                    continue
                own_appointments.append(
                    to_appointment_dto(
                        appointment,
                        position,
                        organ,
                        authorities_by_position.get(position.id, []),
                        today,
                    )
                )
            own_kinships = [k for k in kinships if person_id in (k.person_id, k.relative_id)]
            snapshots.append(
                OfficialSnapshotDTO(
                    person=to_person_dto(person),
                    appointments=tuple(sorted(own_appointments, key=lambda a: a.started_at)),
                    relatives=tuple(to_relative_dtos(person_id, own_kinships, persons)),
                    employments=tuple(
                        to_employment_dto(e) for e in employments if e.person_id == person_id
                    ),
                )
            )
        return snapshots
