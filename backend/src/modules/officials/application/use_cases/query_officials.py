from collections.abc import Sequence
from uuid import UUID

from src.core.utils.iterables import chunked
from src.modules.officials.application.dto.mappers import (
    to_organ_dto,
    to_person_dto,
    to_relative_dtos,
)
from src.modules.officials.application.dto.officials_dto import (
    OfficialSnapshotDTO,
    OrganDTO,
    PersonDTO,
    RelativeDTO,
)
from src.modules.officials.application.interfaces.appointment_repository import (
    AppointmentRepositoryInterface,
)
from src.modules.officials.application.interfaces.organ_repository import (
    OrganRepositoryInterface,
)
from src.modules.officials.application.interfaces.person_repository import (
    PersonRepositoryInterface,
)
from src.modules.officials.application.use_cases.get_official_snapshots import (
    GetOfficialSnapshotsUseCase,
)

MAX_OFFICIALS = 200_000
MAX_NAME_MATCHES = 20
SNAPSHOT_BATCH = 1000


class QueryOfficialsUseCase:
    """Published language контекста officials: запросы на чтение для ACL-адаптеров
    других модулей (risk, appeals, reports, stats). Наружу — только DTO.
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
        self._snapshots = GetOfficialSnapshotsUseCase(
            person_repository, appointment_repository, organ_repository
        )

    async def official_ids(self) -> list[UUID]:
        return await self._appointments.search_official_ids(None, None, MAX_OFFICIALS)

    async def count_officials(self) -> int:
        return await self._appointments.count_officials()

    async def snapshots(self, person_ids: Sequence[UUID]) -> list[OfficialSnapshotDTO]:
        result: list[OfficialSnapshotDTO] = []
        for batch in chunked(person_ids, SNAPSHOT_BATCH):
            result.extend(await self._snapshots.execute(batch))
        return result

    async def persons(self, person_ids: Sequence[UUID]) -> list[PersonDTO]:
        result: list[PersonDTO] = []
        for batch in chunked(person_ids):
            result.extend(to_person_dto(p) for p in await self._persons.get_many(batch))
        return result

    async def persons_by_name(self, name_query: str) -> list[PersonDTO]:
        if len(name_query.strip()) < 3:
            return []
        found = await self._persons.search_by_name(name_query.strip(), MAX_NAME_MATCHES)
        return [to_person_dto(p) for p in found]

    async def relatives(self, person_ids: Sequence[UUID]) -> list[RelativeDTO]:
        kinships = await self._persons.get_kinships(person_ids)
        ids = {k.person_id for k in kinships} | {k.relative_id for k in kinships}
        persons = {p.id: p for p in await self._persons.get_many(list(ids))}
        result: list[RelativeDTO] = []
        for person_id in person_ids:
            own = [k for k in kinships if person_id in (k.person_id, k.relative_id)]
            result.extend(to_relative_dtos(person_id, own, persons))
        return result

    async def organs(self, organ_ids: Sequence[UUID]) -> list[OrganDTO]:
        return [to_organ_dto(o) for o in await self._organs.get_many(organ_ids)]
