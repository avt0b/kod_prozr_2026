from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.counterparties.domain.company import Company, CompanyRole


class CompanyRepositoryInterface(Protocol):
    async def get_many(self, company_ids: Sequence[UUID]) -> list[Company]: ...

    async def list_all(self, limit: int) -> list[Company]:
        """Все компании, не больше limit (снимок для правил риска)."""
        ...

    async def roles_for_persons(self, person_ids: Sequence[UUID]) -> list[CompanyRole]: ...

    async def roles_for_companies(self, company_ids: Sequence[UUID]) -> list[CompanyRole]: ...

    async def upsert_many(self, companies: list[Company], roles: list[CompanyRole]) -> None: ...
