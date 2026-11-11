from fastapi import FastAPI

from src.core.infrastructure.exception_handler import register_problem_handlers
from src.modules.officials.domain.exceptions import (
    InvalidPeriodError,
    OfficialNotFoundError,
    OrganNotFoundError,
    SelfKinshipError,
)


def register_officials_handlers(app: FastAPI) -> None:
    register_problem_handlers(
        app,
        {
            OfficialNotFoundError: 404,
            OrganNotFoundError: 404,
            InvalidPeriodError: 422,
            SelfKinshipError: 422,
        },
    )
