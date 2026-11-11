from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.counterparties.domain.contract import Contract


class ContractRepositoryInterface(Protocol):
    async def find(
        self,
        *,
        customer_organ_ids: Sequence[UUID] | None = None,
        supplier_company_ids: Sequence[UUID] | None = None,
        limit: int,
    ) -> list[Contract]:
        """Контракты по заказчикам и/или поставщикам (AND), новые первыми."""
        ...

    async def upsert_many(self, contracts: list[Contract]) -> None: ...
