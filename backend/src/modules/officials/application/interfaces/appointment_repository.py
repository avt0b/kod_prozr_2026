from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.officials.domain.appointment import Appointment


class AppointmentRepositoryInterface(Protocol):
    async def list_for_persons(self, person_ids: Sequence[UUID]) -> list[Appointment]: ...

    async def search_official_ids(
        self, query: str | None, organ_id: UUID | None, limit: int
    ) -> list[UUID]:
        """id служащих (есть хотя бы одно назначение), отсортированные по ФИО.

        query — подстрока ФИО, organ_id — орган любого из назначений. limit — жёсткий потолок.
        """
        ...

    async def count_officials(self) -> int: ...

    async def upsert_many(self, appointments: list[Appointment]) -> None: ...
