"""E2E: HTTP -> use case -> Postgres -> ответ.

Postgres берётся так (по приоритету):
  1. `TEST_DATABASE_URL` — любая пустая БД (локально удобно поднять свой контейнер);
  2. при `CI=true` — `DATABASE_URL` (в CI Postgres поднят сервисом);
  3. иначе testcontainers (`TEST_POSTGRES_IMAGE`, по умолчанию postgres:16-alpine).
Схемы создаются через Base.metadata.create_all, после каждого теста таблицы очищаются.
"""

import os
import secrets
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer

from src.core.config import Settings
from src.core.infrastructure.auth import issue_access, password_hasher, token_hash
from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.database import get_async_session_maker
from src.core.infrastructure.database.models.auth import AuthSessionModel, UserModel
from src.core.presentation import auth_router
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


@pytest.fixture(autouse=True)
def reset_login_throttle() -> Generator[None, None, None]:
    """Лимит попыток входа общий на процесс: тесты не должны делить его между собой."""
    auth_router._attempts.clear()
    yield
    auth_router._attempts.clear()


@pytest.fixture
def test_settings(database_url: str) -> Settings:
    return Settings(
        app_env="test",
        database_url=database_url,
        llm_base_url=None,
        cors_origins=["http://localhost:5173"],
        auth_secret=SecretStr("test-only-signing-key-never-use-in-production-123"),
        auth_cookie_secure=False,
    )


@pytest.fixture
async def client(engine: AsyncEngine, test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    # ASGITransport не запускает lifespan, поэтому состояние приложения собираем сами.
    app = create_app(test_settings)
    app.state.engine = engine
    app.state.session_maker = get_async_session_maker(engine)
    register_event_handlers(app.state.event_bus, app.state.session_maker)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with app.state.session_maker() as db:
            user = UserModel(
                username="test-analyst",
                password_hash=password_hasher.hash("test-password-long"),
                active=True,
            )
            db.add(user)
            await db.flush()
            session = AuthSessionModel(
                logout_hash=token_hash(secrets.token_urlsafe(32)),
                user_id=user.id,
                refresh_hash=token_hash(secrets.token_urlsafe(48)),
                expires_at=datetime.now(UTC) + timedelta(days=1),
                revoked=False,
            )
            db.add(session)
            await db.flush()
            ac.headers["Authorization"] = "Bearer " + issue_access(user, session, test_settings)
            await db.commit()
        yield ac


EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "example"


@pytest.fixture
async def seeded(engine: AsyncEngine, test_settings: Settings) -> None:
    """data/example: Иванов (R01 + R07), Сидоров (R02), чистый служащий без флагов."""
    async with get_async_session_maker(engine)() as session:
        await load_seed(session, EXAMPLE_DIR, test_settings)
