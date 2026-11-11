from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from src.core.utils.json_files import read_models
from src.modules.counterparties.application.use_cases.import_counterparties_data import (
    CounterpartiesImport,
    ImportCounterpartiesDataUseCase,
)
from src.modules.counterparties.infrastructure.repositories.company_repository import (
    CompanyRepository,
)
from src.modules.counterparties.infrastructure.repositories.contract_repository import (
    ContractRepository,
)
from src.modules.counterparties.presentation.schemas.seed import (
    CompanyRoleSeed,
    CompanySeed,
    ContractSeed,
)

SEED_FILES = ("companies.json", "company_roles.json", "contracts.json")


async def seed_counterparties(session: AsyncSession, data_dir: Path) -> dict[str, int]:
    data = CounterpartiesImport(
        companies=[s.to_entity() for s in read_models(CompanySeed, data_dir / "companies.json")],
        company_roles=[
            s.to_entity() for s in read_models(CompanyRoleSeed, data_dir / "company_roles.json")
        ],
        contracts=[s.to_entity() for s in read_models(ContractSeed, data_dir / "contracts.json")],
    )
    use_case = ImportCounterpartiesDataUseCase(
        CompanyRepository(session), ContractRepository(session), SqlAlchemyUnitOfWork(session)
    )
    return await use_case.execute(data)
