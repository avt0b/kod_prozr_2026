from fastapi import FastAPI

from src.core.infrastructure.exception_handler import register_problem_handlers
from src.modules.risk.domain.exceptions import InvalidGraphDepthError, RiskSubjectNotFoundError


def register_risk_handlers(app: FastAPI) -> None:
    register_problem_handlers(app, {RiskSubjectNotFoundError: 404, InvalidGraphDepthError: 422})
