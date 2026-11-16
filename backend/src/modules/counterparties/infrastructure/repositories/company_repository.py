from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.upsert import upsert_rows
from src.modules.counterparties.application.interfaces.company_repository import (
    CompanyRepositoryInterface,
)
from src.modules.counterparties.domain.company import Company, CompanyRole
from src.modules.counterparties.infrastructure.database.models import (
    CompanyModel,
    CompanyRoleModel,
)


class CompanyRepository(CompanyRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_many(self, company_ids: Sequence[UUID]) -> list[Company]:
        if not company_ids:
            return []
        rows = await self._session.scalars(
            select(CompanyModel).where(CompanyModel.id.in_(list(company_ids)))
        )
        return [r.to_entity() for r in rows]

    async def list_all(self, limit: int) -> list[Company]:
        rows = await self._session.scalars(
            select(CompanyModel).order_by(CompanyModel.id).limit(limit)
        )
        return [r.to_entity() for r in rows]

    async def roles_for_persons(self, person_ids: Sequence[UUID]) -> list[CompanyRole]:
        if not person_ids:
            return []
        rows = await self._session.scalars(
            select(CompanyRoleModel).where(CompanyRoleModel.person_id.in_(list(person_ids)))
        )
        return [r.to_entity() for r in rows]

    async def roles_for_companies(self, company_ids: Sequence[UUID]) -> list[CompanyRole]:
        if not company_ids:
            return []
        rows = await self._session.scalars(
            select(CompanyRoleModel).where(CompanyRoleModel.company_id.in_(list(company_ids)))
        )
        return [r.to_entity() for r in rows]

    async def upsert_many(self, companies: list[Company], roles: list[CompanyRole]) -> None:
        await upsert_rows(self._session, CompanyModel, [CompanyModel.row(c) for c in companies])
        await upsert_rows(self._session, CompanyRoleModel, [CompanyRoleModel.row(r) for r in roles])
