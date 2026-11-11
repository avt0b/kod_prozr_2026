from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.infrastructure.dependencies import (
    get_llm_client,
    get_session,
    get_settings,
    get_unit_of_work,
)
from src.core.infrastructure.interfaces.llm_client import LLMClientInterface
from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.modules.reports.application.interfaces.dossier_source import DossierSourceInterface
from src.modules.reports.application.interfaces.report_repository import (
    ReportRepositoryInterface,
)
from src.modules.reports.application.interfaces.report_writer import ReportWriterInterface
from src.modules.reports.application.use_cases.create_report_draft import (
    CreateReportDraftUseCase,
)
from src.modules.reports.application.use_cases.get_report_draft import GetReportDraftUseCase
from src.modules.reports.infrastructure.adapters.fallback_writer import FallbackReportWriter
from src.modules.reports.infrastructure.adapters.llm_writer import LLMReportWriter
from src.modules.reports.infrastructure.adapters.template_writer import TemplateReportWriter
from src.modules.reports.infrastructure.repositories.report_repository import ReportRepository


def get_dossier_source() -> DossierSourceInterface:
    raise NotImplementedError("Overridden in src/web/create_app.py (dependency_overrides)")


def get_report_writer(
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[LLMClientInterface | None, Depends(get_llm_client)],
) -> ReportWriterInterface:
    template = TemplateReportWriter()
    if llm is None:
        return template
    return FallbackReportWriter(LLMReportWriter(llm, settings.llm_model), template)


def get_report_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportRepositoryInterface:
    return ReportRepository(session)


def get_create_report_use_case(
    dossiers: Annotated[DossierSourceInterface, Depends(get_dossier_source)],
    writer: Annotated[ReportWriterInterface, Depends(get_report_writer)],
    repository: Annotated[ReportRepositoryInterface, Depends(get_report_repository)],
    unit_of_work: Annotated[UnitOfWorkInterface, Depends(get_unit_of_work)],
) -> CreateReportDraftUseCase:
    return CreateReportDraftUseCase(dossiers, writer, repository, unit_of_work)


def get_get_report_use_case(
    repository: Annotated[ReportRepositoryInterface, Depends(get_report_repository)],
) -> GetReportDraftUseCase:
    return GetReportDraftUseCase(repository)
