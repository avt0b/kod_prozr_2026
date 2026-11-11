from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.events.event_bus import EventBus
from src.core.infrastructure.dependencies import (
    get_event_bus,
    get_llm_client,
    get_session,
    get_settings,
    get_unit_of_work,
)
from src.core.infrastructure.interfaces.llm_client import LLMClientInterface
from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.modules.appeals.application.interfaces.appeal_analyzer import AppealAnalyzer
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.application.services.appeal_analysis import AppealAnalysisService
from src.modules.appeals.application.use_cases.create_appeal import CreateAppealUseCase
from src.modules.appeals.application.use_cases.get_appeal import GetAppealUseCase
from src.modules.appeals.application.use_cases.list_appeals import ListAppealsUseCase
from src.modules.appeals.application.use_cases.reanalyze_appeal import ReanalyzeAppealUseCase
from src.modules.appeals.infrastructure.adapters.fallback_analyzer import FallbackAppealAnalyzer
from src.modules.appeals.infrastructure.adapters.llm_analyzer import LLMAppealAnalyzer
from src.modules.appeals.infrastructure.adapters.rule_based_analyzer import (
    RuleBasedAppealAnalyzer,
)
from src.modules.appeals.infrastructure.repositories.appeal_repository import AppealRepository

# --- Порт к officials: реализацию подставляет src/web/create_app.py --------------------------


def get_person_directory() -> PersonDirectoryInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


# --- Модуль ----------------------------------------------------------------------------------


def build_appeal_analyzer(settings: Settings, llm: LLMClientInterface | None) -> AppealAnalyzer:
    """LLM включена (LLM_BASE_URL задан) -> LLM с фоллбэком на правила, иначе только правила."""
    rules = RuleBasedAppealAnalyzer()
    if llm is None:
        return rules
    return FallbackAppealAnalyzer(LLMAppealAnalyzer(llm, settings.llm_model), rules)


def get_appeal_analyzer(
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[LLMClientInterface | None, Depends(get_llm_client)],
) -> AppealAnalyzer:
    return build_appeal_analyzer(settings, llm)


def get_appeal_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppealRepositoryInterface:
    return AppealRepository(session)


def get_appeal_analysis_service(
    analyzer: Annotated[AppealAnalyzer, Depends(get_appeal_analyzer)],
    directory: Annotated[PersonDirectoryInterface, Depends(get_person_directory)],
) -> AppealAnalysisService:
    return AppealAnalysisService(analyzer, directory)


def get_create_appeal_use_case(
    repository: Annotated[AppealRepositoryInterface, Depends(get_appeal_repository)],
    analysis: Annotated[AppealAnalysisService, Depends(get_appeal_analysis_service)],
    directory: Annotated[PersonDirectoryInterface, Depends(get_person_directory)],
    unit_of_work: Annotated[UnitOfWorkInterface, Depends(get_unit_of_work)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> CreateAppealUseCase:
    return CreateAppealUseCase(repository, analysis, directory, unit_of_work, event_bus)


def get_reanalyze_appeal_use_case(
    repository: Annotated[AppealRepositoryInterface, Depends(get_appeal_repository)],
    analysis: Annotated[AppealAnalysisService, Depends(get_appeal_analysis_service)],
    directory: Annotated[PersonDirectoryInterface, Depends(get_person_directory)],
    unit_of_work: Annotated[UnitOfWorkInterface, Depends(get_unit_of_work)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> ReanalyzeAppealUseCase:
    return ReanalyzeAppealUseCase(repository, analysis, directory, unit_of_work, event_bus)


def get_get_appeal_use_case(
    repository: Annotated[AppealRepositoryInterface, Depends(get_appeal_repository)],
    directory: Annotated[PersonDirectoryInterface, Depends(get_person_directory)],
) -> GetAppealUseCase:
    return GetAppealUseCase(repository, directory)


def get_list_appeals_use_case(
    repository: Annotated[AppealRepositoryInterface, Depends(get_appeal_repository)],
    directory: Annotated[PersonDirectoryInterface, Depends(get_person_directory)],
) -> ListAppealsUseCase:
    return ListAppealsUseCase(repository, directory)
