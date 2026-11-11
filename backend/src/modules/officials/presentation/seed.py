"""Входной адаптер загрузки синтетики для контекста officials (как роутер, только из файлов)."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from src.core.utils.json_files import read_models
from src.modules.officials.application.use_cases.import_officials_data import (
    ImportOfficialsDataUseCase,
    OfficialsImport,
)
from src.modules.officials.infrastructure.repositories.appointment_repository import (
    AppointmentRepository,
)
from src.modules.officials.infrastructure.repositories.organ_repository import OrganRepository
from src.modules.officials.infrastructure.repositories.person_repository import (
    PersonRepository,
)
from src.modules.officials.presentation.schemas.seed import (
    AppointmentSeed,
    AuthoritySeed,
    EmploymentSeed,
    KinshipSeed,
    OrganSeed,
    PersonSeed,
    PositionSeed,
)

SEED_FILES = (
    "organs.json",
    "positions.json",
    "authorities.json",
    "persons.json",
    "kinships.json",
    "employments.json",
    "appointments.json",
)


async def seed_officials(session: AsyncSession, data_dir: Path) -> dict[str, int]:
    data = OfficialsImport(
        organs=[s.to_entity() for s in read_models(OrganSeed, data_dir / "organs.json")],
        positions=[s.to_entity() for s in read_models(PositionSeed, data_dir / "positions.json")],
        authorities=[
            s.to_entity() for s in read_models(AuthoritySeed, data_dir / "authorities.json")
        ],
        persons=[s.to_entity() for s in read_models(PersonSeed, data_dir / "persons.json")],
        kinships=[s.to_entity() for s in read_models(KinshipSeed, data_dir / "kinships.json")],
        employments=[
            s.to_entity() for s in read_models(EmploymentSeed, data_dir / "employments.json")
        ],
        appointments=[
            s.to_entity() for s in read_models(AppointmentSeed, data_dir / "appointments.json")
        ],
    )
    use_case = ImportOfficialsDataUseCase(
        OrganRepository(session),
        PersonRepository(session),
        AppointmentRepository(session),
        SqlAlchemyUnitOfWork(session),
    )
    return await use_case.execute(data)
