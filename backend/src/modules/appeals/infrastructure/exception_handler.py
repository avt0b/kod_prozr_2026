from fastapi import FastAPI

from src.core.infrastructure.exception_handler import register_problem_handlers
from src.modules.appeals.domain.exceptions import (
    AppealClosedError,
    AppealNotFoundError,
    EmptyAppealTextError,
    InvalidAnalysisError,
    InvalidAppealStatusTransitionError,
)


def register_appeals_handlers(app: FastAPI) -> None:
    register_problem_handlers(
        app,
        {
            AppealNotFoundError: 404,
            AppealClosedError: 409,
            InvalidAppealStatusTransitionError: 409,
            EmptyAppealTextError: 422,
            InvalidAnalysisError: 422,
        },
    )
