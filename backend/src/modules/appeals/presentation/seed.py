"""Входной адаптер загрузки синтетики для контекста appeals."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from src.core.utils.json_files import read_models
from src.modules.appeals.application.interfaces.appeal_analyzer import AppealAnalyzer
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.application.services.appeal_analysis import AppealAnalysisService
from src.modules.appeals.application.use_cases.import_appeals import ImportAppealsUseCase
from src.modules.appeals.infrastructure.repositories.appeal_repository import AppealRepository
from src.modules.appeals.presentation.schemas.seed import AppealSeed

SEED_FILES = ("appeals.json",)


async def seed_appeals(
    session: AsyncSession,
    data_dir: Path,
    analyzer: AppealAnalyzer,
    directory: PersonDirectoryInterface,
    analyze: bool = True,
) -> dict[str, int]:
    appeals = [s.to_entity() for s in read_models(AppealSeed, data_dir / "appeals.json")]
    use_case = ImportAppealsUseCase(
        AppealRepository(session),
        AppealAnalysisService(analyzer, directory),
        SqlAlchemyUnitOfWork(session),
    )
    return await use_case.execute(appeals, analyze=analyze)
