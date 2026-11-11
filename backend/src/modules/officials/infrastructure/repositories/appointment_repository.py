from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.upsert import upsert_rows
from src.modules.officials.application.interfaces.appointment_repository import (
    AppointmentRepositoryInterface,
)
from src.modules.officials.domain.appointment import Appointment
from src.modules.officials.infrastructure.database.models import (
    AppointmentModel,
    PersonModel,
    PositionModel,
)
from src.modules.officials.infrastructure.repositories.person_repository import escape_like


class AppointmentRepository(AppointmentRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_persons(self, person_ids: Sequence[UUID]) -> list[Appointment]:
        if not person_ids:
            return []
        rows = await self._session.scalars(
            select(AppointmentModel).where(AppointmentModel.person_id.in_(list(person_ids)))
        )
        return [r.to_entity() for r in rows]

    async def search_official_ids(
        self, query: str | None, organ_id: UUID | None, limit: int
    ) -> list[UUID]:
        officials = select(AppointmentModel.person_id)
        if organ_id is not None:
            officials = officials.join(
                PositionModel, PositionModel.id == AppointmentModel.position_id
            ).where(PositionModel.organ_id == organ_id)

        stmt = select(PersonModel.id).where(PersonModel.id.in_(officials))
        if query and query.strip():
            pattern = f"%{escape_like(query.strip())}%"
            stmt = stmt.where(PersonModel.full_name.ilike(pattern, escape="\\"))
        stmt = stmt.order_by(PersonModel.full_name, PersonModel.id).limit(limit)
        return list(await self._session.scalars(stmt))

    async def count_officials(self) -> int:
        total = await self._session.scalar(select(func.count(distinct(AppointmentModel.person_id))))
        return total or 0

    async def upsert_many(self, appointments: list[Appointment]) -> None:
        await upsert_rows(
            self._session, AppointmentModel, [AppointmentModel.row(a) for a in appointments]
        )
