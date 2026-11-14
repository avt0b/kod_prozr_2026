"""Входной адаптер загрузки синтетики для контекста appeals."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from src.core.infrastructure.logger import get_logger
from src.core.utils.json_files import read_models
from src.modules.appeals.application.interfaces.appeal_analyzer import AppealAnalyzer
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.application.services.appeal_analysis import AppealAnalysisService
from src.modules.appeals.application.use_cases.import_appeals import ImportAppealsUseCase
from src.modules.appeals.infrastructure.repositories.appeal_repository import AppealRepository
from src.modules.appeals.presentation.dependencies import get_person_matcher
from src.modules.appeals.presentation.schemas.seed import AppealSeed

logger = get_logger("seed")

SEED_FILES = ("appeals.json",)


async def seed_appeals(
    session: AsyncSession,
    data_dir: Path,
    analyzer: AppealAnalyzer,
    directory: PersonDirectoryInterface,
    analyze: bool = True,
    reanalyze: bool = False,
) -> dict[str, int]:
    seeds = read_models(AppealSeed, data_dir / "appeals.json")
    if reanalyze:  # AI-06: предрасчёт заново — сохранённый анализ игнорируем
        seeds = [
            s.model_copy(update={"analysis": None, "status": "new", "linked_person_ids": []})
            for s in seeds
        ]
    appeals = [s.to_entity() for s in seeds]
    if analyze and not reanalyze and any(a.analysis is not None for a in appeals):
        # AI-06: сиды с предрасчётом. Оставшиеся `new` (демо-обращение) разбираются вживую.
        logger.info("Appeals have precomputed analysis: unanalyzed ones stay new")
        analyze = False
    use_case = ImportAppealsUseCase(
        AppealRepository(session),
        AppealAnalysisService(analyzer, directory, get_person_matcher()),
        SqlAlchemyUnitOfWork(session),
    )
    return await use_case.execute(appeals, analyze=analyze)
