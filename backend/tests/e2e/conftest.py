"""E2E: HTTP -> use case -> Postgres -> ответ.

Postgres берётся так (по приоритету):
  1. `TEST_DATABASE_URL` — любая пустая БД (локально удобно поднять свой контейнер);
  2. при `CI=true` — `DATABASE_URL` (в CI Postgres поднят сервисом);
  3. иначе testcontainers (`TEST_POSTGRES_IMAGE`, по умолчанию postgres:16-alpine).
Схемы создаются через Base.metadata.create_all, после каждого теста таблицы очищаются.
"""

import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from src.core.config import Settings
from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.database import get_async_session_maker
from src.modules.appeals.infrastructure.database import models as appeals_models
from src.modules.counterparties.infrastructure.database import models as counterparties_models
from src.modules.officials.infrastructure.database import models as officials_models
from src.modules.reports.infrastructure.database import models as reports_models
from src.modules.risk.infrastructure.database import models as risk_models
from src.seed.loader import load_seed
from src.web.create_app import create_app
from src.web.event_handlers import register_event_handlers

_ = (appeals_models, counterparties_models, officials_models, reports_models, risk_models)


@pytest.fixture(scope="session")
def database_url() -> Generator[str, None, None]:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        yield explicit
        return
    if os.environ.get("CI") == "true":
        yield os.environ["DATABASE_URL"]
        return
    image = os.environ.get("TEST_POSTGRES_IMAGE", "postgres:16-alpine")
    with PostgresContainer(image, driver="asyncpg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
async def engine(database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        tables = ", ".join(
            f'"{t.schema}"."{t.name}"' for t in Base.metadata.sorted_tables if t.schema
        )
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    await engine.dispose()


@pytest.fixture
def test_settings(database_url: str) -> Settings:
    return Settings(
        app_env="test",
        database_url=database_url,
        llm_base_url=None,
        cors_origins=["http://localhost:5173"],
    )


@pytest.fixture
async def client(engine: AsyncEngine, test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    # ASGITransport не запускает lifespan, поэтому состояние приложения собираем сами.
    app = create_app(test_settings)
    app.state.engine = engine
    app.state.session_maker = get_async_session_maker(engine)
    register_event_handlers(app.state.event_bus, app.state.session_maker)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "example"


@pytest.fixture
async def seeded(engine: AsyncEngine, test_settings: Settings) -> None:
    """data/example: Иванов (R01 + R07), Сидоров (R02), чистый служащий без флагов."""
    async with get_async_session_maker(engine)() as session:
        await load_seed(session, EXAMPLE_DIR, test_settings)
