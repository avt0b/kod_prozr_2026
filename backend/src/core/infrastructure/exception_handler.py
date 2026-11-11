from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.exceptions import (
    ConflictError,
    DomainError,
    DomainValidationError,
    ExternalServiceError,
    InfrastructureError,
    NotFoundError,
)
from src.core.infrastructure.logger import get_logger
from src.core.schemas.problem_details import ProblemDetails

logger = get_logger(__name__)

PROBLEM_JSON = "application/problem+json"

ExceptionHandler = Callable[[Request, Any], Awaitable[JSONResponse]]


def problem_response(
    request: Request,
    status: int,
    title: str,
    detail: str | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    problem = ProblemDetails(
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        errors=errors or [],
    )
    return JSONResponse(
        status_code=status, content=jsonable_encoder(problem.to_dict()), media_type=PROBLEM_JSON
    )


def problem_handler(status: int) -> ExceptionHandler:
    """Обработчик «исключение -> ProblemDetails с данным статусом». title = имя класса."""

    async def handler(request: Request, exc: Exception) -> JSONResponse:
        message = getattr(exc, "message", "") or str(exc)
        log = logger.warning if status >= 500 else logger.info
        log("{} {} -> {} {}", request.method, request.url.path, status, type(exc).__name__)
        return problem_response(request, status, type(exc).__name__, message or None)

    return handler


def register_problem_handlers(app: FastAPI, mapping: Mapping[type[Exception], int]) -> None:
    """Модули регистрируют свои исключения этим помощником в infrastructure/exception_handler.py."""
    for exc_type, status in mapping.items():
        app.add_exception_handler(exc_type, problem_handler(status))


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await handle_generic_exception(request, exc)
    errors = [
        {"loc": list(err.get("loc", ())), "msg": err.get("msg", ""), "type": err.get("type", "")}
        for err in exc.errors()
    ]
    return problem_response(
        request, 422, "ValidationError", "Request validation failed", errors=errors
    )


async def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return await handle_generic_exception(request, exc)
    title = "NotFound" if exc.status_code == 404 else "HTTPError"
    return problem_response(request, exc.status_code, title, str(exc.detail))


async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unexpected error on {} {}", request.method, request.url.path)
    return problem_response(request, 500, "InternalServerError")


# Базовые классы: исключение модуля, унаследованное от NotFoundError, само станет 404 —
# Starlette ищет обработчик по MRO.
CORE_STATUS_MAP: dict[type[Exception], int] = {
    DomainError: 400,
    NotFoundError: 404,
    ConflictError: 409,
    DomainValidationError: 422,
    InfrastructureError: 500,
    ExternalServiceError: 503,
}


def register_core_handlers(app: FastAPI) -> None:
    register_problem_handlers(app, CORE_STATUS_MAP)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_generic_exception)
