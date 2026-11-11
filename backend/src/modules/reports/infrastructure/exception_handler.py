from fastapi import FastAPI

from src.core.infrastructure.exception_handler import register_problem_handlers
from src.modules.reports.domain.exceptions import (
    EmptyReportTextError,
    ReportDraftNotFoundError,
    ReportSubjectNotFoundError,
)


def register_reports_handlers(app: FastAPI) -> None:
    register_problem_handlers(
        app,
        {
            ReportDraftNotFoundError: 404,
            ReportSubjectNotFoundError: 404,
            EmptyReportTextError: 422,
        },
    )
