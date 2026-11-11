from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.infrastructure.database.database import get_async_session_maker, get_engine
from src.core.infrastructure.dependencies import get_session
from src.core.infrastructure.events import InMemoryEventBus
from src.core.infrastructure.exception_handler import register_core_handlers
from src.core.infrastructure.llm import OpenAICompatibleLLMClient
from src.core.infrastructure.logger import configure_logging, get_logger
from src.modules.appeals.infrastructure.exception_handler import register_appeals_handlers
from src.modules.appeals.presentation.api.appeals_router import router as appeals_router
from src.modules.assistant.infrastructure.exception_handler import register_assistant_handlers
from src.modules.assistant.presentation.api.assistant_router import router as assistant_router
from src.modules.counterparties.infrastructure.exception_handler import (
    register_counterparties_handlers,
)
from src.modules.officials.infrastructure.exception_handler import register_officials_handlers
from src.modules.officials.presentation.api.officials_router import router as officials_router
from src.modules.officials.presentation.api.organs_router import router as organs_router
from src.modules.reports.infrastructure.exception_handler import register_reports_handlers
from src.modules.reports.presentation.api.reports_router import router as reports_router
from src.modules.risk.infrastructure.exception_handler import register_risk_handlers
from src.modules.risk.presentation.api.risk_router import router as risk_router
from src.modules.stats.presentation.api.stats_router import router as stats_router
from src.web.dependencies import DEPENDENCY_OVERRIDES
from src.web.event_handlers import register_event_handlers

logger = get_logger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings
    engine = get_engine(settings.database_url, echo=settings.db_echo)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established")
    except Exception as exc:  # стартуем и без БД: /health ответит 503
        logger.error("Database is unavailable at startup: {}", type(exc).__name__)

    app.state.engine = engine
    app.state.session_maker = get_async_session_maker(engine)
    register_event_handlers(app.state.event_bus, app.state.session_maker)
    yield
    await engine.dispose()


def create_app(settings: Settings) -> FastAPI:
    configure_logging(settings.log_level)
    app = FastAPI(
        title=settings.project_name,
        description="API рабочего места аналитика по профилактике коррупции",
        version=settings.version,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.event_bus = InMemoryEventBus()
    app.state.llm_client = (
        OpenAICompatibleLLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value() if settings.llm_api_key else None,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )
        if settings.llm_base_url
        else None
    )
    logger.info("LLM: {}", settings.llm_model if settings.llm_base_url else "disabled (rules)")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_core_handlers(app)
    register_officials_handlers(app)
    register_counterparties_handlers(app)
    register_risk_handlers(app)
    register_appeals_handlers(app)
    register_reports_handlers(app)
    register_assistant_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(stats_router)
    api.include_router(organs_router)
    api.include_router(officials_router)
    api.include_router(risk_router)
    api.include_router(appeals_router)
    api.include_router(reports_router)
    api.include_router(assistant_router)
    app.include_router(api)

    # Межмодульные порты: модули объявили заглушки, реализации — из composition root.
    app.dependency_overrides.update(DEPENDENCY_OVERRIDES)

    @app.get("/health", tags=["system"], response_model=None)
    async def health(
        session: AsyncSession = Depends(get_session),
    ) -> dict[str, str] | JSONResponse:
        try:
            await session.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse(
                status_code=503, content={"status": "unavailable", "database": "unavailable"}
            )
        return {"status": "ok"}

    return app
