from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.risk.domain.facts import CompanyFacts, CompanyRoleFacts, ContractFacts


class CounterpartiesSourceInterface(Protocol):
    async def roles_for_persons(self, person_ids: Sequence[UUID]) -> list[CompanyRoleFacts]: ...

    async def roles_for_companies(self, company_ids: Sequence[UUID]) -> list[CompanyRoleFacts]: ...

    async def companies(self, company_ids: Sequence[UUID]) -> list[CompanyFacts]: ...

    async def all_companies(self, limit: int) -> list[CompanyFacts]: ...

    async def contracts(
        self,
        *,
        customer_organ_ids: Sequence[UUID] | None = None,
        supplier_company_ids: Sequence[UUID] | None = None,
        limit: int,
    ) -> list[ContractFacts]: ...
