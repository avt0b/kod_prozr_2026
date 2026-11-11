from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.officials.domain.person import Employment, Kinship, Person


class PersonRepositoryInterface(Protocol):
    async def get(self, person_id: UUID) -> Person | None: ...

    async def get_many(self, person_ids: Sequence[UUID]) -> list[Person]: ...

    async def get_kinships(self, person_ids: Sequence[UUID]) -> list[Kinship]:
        """Записи родства, где человек стоит с любой стороны (person_id или relative_id)."""
        ...

    async def get_employments(self, person_ids: Sequence[UUID]) -> list[Employment]: ...

    async def search_by_name(self, name_query: str, limit: int) -> list[Person]:
        """Поиск по подстроке ФИО без учёта регистра."""
        ...

    async def upsert_many(
        self, persons: list[Person], kinships: list[Kinship], employments: list[Employment]
    ) -> None: ...
