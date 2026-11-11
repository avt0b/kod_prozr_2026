from dataclasses import dataclass, field

from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.core.infrastructure.logger import get_logger
from src.modules.counterparties.application.interfaces.company_repository import (
    CompanyRepositoryInterface,
)
from src.modules.counterparties.application.interfaces.contract_repository import (
    ContractRepositoryInterface,
)
from src.modules.counterparties.domain.company import Company, CompanyRole
from src.modules.counterparties.domain.contract import Contract

logger = get_logger(__name__)


@dataclass
class CounterpartiesImport:
    companies: list[Company] = field(default_factory=list)
    company_roles: list[CompanyRole] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)


class ImportCounterpartiesDataUseCase:
    def __init__(
        self,
        company_repository: CompanyRepositoryInterface,
        contract_repository: ContractRepositoryInterface,
        unit_of_work: UnitOfWorkInterface,
    ) -> None:
        self._companies = company_repository
        self._contracts = contract_repository
        self._unit_of_work = unit_of_work

    async def execute(self, data: CounterpartiesImport) -> dict[str, int]:
        async with self._unit_of_work:
            await self._companies.upsert_many(data.companies, data.company_roles)
            await self._contracts.upsert_many(data.contracts)
            await self._unit_of_work.commit()
        counts = {
            "companies": len(data.companies),
            "company_roles": len(data.company_roles),
            "contracts": len(data.contracts),
        }
        logger.info("Counterparties data imported: {}", counts)
        return counts
