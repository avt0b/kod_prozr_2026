from fastapi import FastAPI

from src.core.infrastructure.exception_handler import register_problem_handlers
from src.modules.counterparties.domain.exceptions import (
    InvalidContractAmountError,
    InvalidRolePeriodError,
    InvalidShareError,
)


def register_counterparties_handlers(app: FastAPI) -> None:
    register_problem_handlers(
        app,
        {InvalidShareError: 422, InvalidContractAmountError: 422, InvalidRolePeriodError: 422},
    )
