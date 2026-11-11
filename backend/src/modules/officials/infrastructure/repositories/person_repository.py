from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.upsert import upsert_rows
from src.modules.officials.application.interfaces.person_repository import (
    PersonRepositoryInterface,
)
from src.modules.officials.domain.person import Employment, Kinship, Person
from src.modules.officials.infrastructure.database.models import (
    EmploymentModel,
    KinshipModel,
    PersonModel,
)


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class PersonRepository(PersonRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, person_id: UUID) -> Person | None:
        model = await self._session.get(PersonModel, person_id)
        return model.to_entity() if model else None

    async def get_many(self, person_ids: Sequence[UUID]) -> list[Person]:
        if not person_ids:
            return []
        rows = await self._session.scalars(
            select(PersonModel).where(PersonModel.id.in_(list(person_ids)))
        )
        return [r.to_entity() for r in rows]

    async def get_kinships(self, person_ids: Sequence[UUID]) -> list[Kinship]:
        if not person_ids:
            return []
        ids = list(person_ids)
        rows = await self._session.scalars(
            select(KinshipModel).where(
                or_(KinshipModel.person_id.in_(ids), KinshipModel.relative_id.in_(ids))
            )
        )
        return [r.to_entity() for r in rows]

    async def get_employments(self, person_ids: Sequence[UUID]) -> list[Employment]:
        if not person_ids:
            return []
        rows = await self._session.scalars(
            select(EmploymentModel).where(EmploymentModel.person_id.in_(list(person_ids)))
        )
        return [r.to_entity() for r in rows]

    async def search_by_name(self, name_query: str, limit: int) -> list[Person]:
        pattern = f"%{escape_like(name_query)}%"
        rows = await self._session.scalars(
            select(PersonModel)
            .where(PersonModel.full_name.ilike(pattern, escape="\\"))
            .order_by(PersonModel.full_name)
            .limit(limit)
        )
        return [r.to_entity() for r in rows]

    async def upsert_many(
        self, persons: list[Person], kinships: list[Kinship], employments: list[Employment]
    ) -> None:
        await upsert_rows(self._session, PersonModel, [PersonModel.row(p) for p in persons])
        await upsert_rows(self._session, KinshipModel, [KinshipModel.row(k) for k in kinships])
        await upsert_rows(
            self._session, EmploymentModel, [EmploymentModel.row(e) for e in employments]
        )
