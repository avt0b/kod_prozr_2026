from collections.abc import Sequence
from uuid import UUID

from src.modules.counterparties.application.dto.counterparties_dto import (
    CompanyDTO,
    CompanyRoleDTO,
    ContractDTO,
)
from src.modules.counterparties.application.interfaces.company_repository import (
    CompanyRepositoryInterface,
)
from src.modules.counterparties.application.interfaces.contract_repository import (
    ContractRepositoryInterface,
)

MAX_CONTRACTS = 100_000
MAX_COMPANIES = 100_000


class QueryCounterpartiesUseCase:
    """Запросы на чтение для ACL-адаптеров других контекстов (officials, risk).

    Это published language контекста: наружу уходят только DTO, без доменных сущностей.
    """

    def __init__(
        self,
        company_repository: CompanyRepositoryInterface,
        contract_repository: ContractRepositoryInterface,
    ) -> None:
        self._companies = company_repository
        self._contracts = contract_repository

    async def companies(self, company_ids: Sequence[UUID]) -> list[CompanyDTO]:
        return [CompanyDTO.from_entity(c) for c in await self._companies.get_many(company_ids)]

    async def all_companies(self, limit: int = MAX_COMPANIES) -> list[CompanyDTO]:
        found = await self._companies.list_all(min(limit, MAX_COMPANIES))
        return [CompanyDTO.from_entity(c) for c in found]

    async def roles_for_persons(self, person_ids: Sequence[UUID]) -> list[CompanyRoleDTO]:
        roles = await self._companies.roles_for_persons(person_ids)
        return [CompanyRoleDTO.from_entity(r) for r in roles]

    async def roles_for_companies(self, company_ids: Sequence[UUID]) -> list[CompanyRoleDTO]:
        roles = await self._companies.roles_for_companies(company_ids)
        return [CompanyRoleDTO.from_entity(r) for r in roles]

    async def contracts(
        self,
        *,
        customer_organ_ids: Sequence[UUID] | None = None,
        supplier_company_ids: Sequence[UUID] | None = None,
        limit: int = MAX_CONTRACTS,
    ) -> list[ContractDTO]:
        found = await self._contracts.find(
            customer_organ_ids=customer_organ_ids,
            supplier_company_ids=supplier_company_ids,
            limit=min(limit, MAX_CONTRACTS),
        )
        return [ContractDTO.from_entity(c) for c in found]
