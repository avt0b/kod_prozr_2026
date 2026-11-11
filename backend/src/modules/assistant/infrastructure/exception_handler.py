from fastapi import FastAPI

from src.core.infrastructure.exception_handler import register_problem_handlers
from src.modules.assistant.domain.exceptions import EmptyQuestionError


def register_assistant_handlers(app: FastAPI) -> None:
    register_problem_handlers(app, {EmptyQuestionError: 422})
