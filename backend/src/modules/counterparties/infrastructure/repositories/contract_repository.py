from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.upsert import upsert_rows
from src.modules.counterparties.application.interfaces.contract_repository import (
    ContractRepositoryInterface,
)
from src.modules.counterparties.domain.contract import Contract
from src.modules.counterparties.infrastructure.database.models import ContractModel


class ContractRepository(ContractRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(
        self,
        *,
        customer_organ_ids: Sequence[UUID] | None = None,
        supplier_company_ids: Sequence[UUID] | None = None,
        limit: int,
    ) -> list[Contract]:
        stmt = select(ContractModel)
        if customer_organ_ids is not None:
            if not customer_organ_ids:
                return []
            stmt = stmt.where(ContractModel.customer_organ_id.in_(list(customer_organ_ids)))
        if supplier_company_ids is not None:
            if not supplier_company_ids:
                return []
            stmt = stmt.where(ContractModel.supplier_company_id.in_(list(supplier_company_ids)))
        stmt = stmt.order_by(ContractModel.signed_at.desc()).limit(limit)
        return [r.to_entity() for r in await self._session.scalars(stmt)]

    async def upsert_many(self, contracts: list[Contract]) -> None:
        await upsert_rows(self._session, ContractModel, [ContractModel.row(c) for c in contracts])
