from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dto import Page, PageRequest
from src.core.infrastructure.database.upsert import upsert_rows
from src.modules.officials.application.interfaces.organ_repository import (
    OrganRepositoryInterface,
)
from src.modules.officials.domain.organ import Authority, Organ, Position
from src.modules.officials.infrastructure.database.models import (
    AuthorityModel,
    OrganModel,
    PositionModel,
)


class OrganRepository(OrganRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_page(self, page: PageRequest) -> Page[Organ]:
        total = await self._session.scalar(select(func.count()).select_from(OrganModel))
        rows = await self._session.scalars(
            select(OrganModel)
            .order_by(OrganModel.region, OrganModel.name)
            .limit(page.limit)
            .offset(page.offset)
        )
        return Page(items=[r.to_entity() for r in rows], total=total or 0)

    async def get_many(self, organ_ids: Sequence[UUID]) -> list[Organ]:
        if not organ_ids:
            return []
        rows = await self._session.scalars(
            select(OrganModel).where(OrganModel.id.in_(list(organ_ids)))
        )
        return [r.to_entity() for r in rows]

    async def get_positions(self, position_ids: Sequence[UUID]) -> list[Position]:
        if not position_ids:
            return []
        rows = await self._session.scalars(
            select(PositionModel).where(PositionModel.id.in_(list(position_ids)))
        )
        return [r.to_entity() for r in rows]

    async def get_authorities(self, position_ids: Sequence[UUID]) -> list[Authority]:
        if not position_ids:
            return []
        rows = await self._session.scalars(
            select(AuthorityModel).where(AuthorityModel.position_id.in_(list(position_ids)))
        )
        return [r.to_entity() for r in rows]

    async def upsert_many(
        self, organs: list[Organ], positions: list[Position], authorities: list[Authority]
    ) -> None:
        await upsert_rows(self._session, OrganModel, [OrganModel.row(o) for o in organs])
        await upsert_rows(self._session, PositionModel, [PositionModel.row(p) for p in positions])
        await upsert_rows(
            self._session, AuthorityModel, [AuthorityModel.row(a) for a in authorities]
        )
