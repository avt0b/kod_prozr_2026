"""Alembic env. Одна схема Postgres на bounded context; в public — только alembic_version.

Alembic смотрит только на схемы своих моделей (include_schemas + include_name), как в optimus.
Новый модуль с таблицами -> импорт его models ниже, иначе autogenerate их не увидит.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.core.config import get_settings_from_env
from src.core.infrastructure.database.base import Base
from src.core.infrastructure.database.models import audit_log
from src.core.infrastructure.database.models import auth as auth_models

# Импорт всех моделей, чтобы они попали в Base.metadata.
from src.modules.appeals.infrastructure.database import models as appeals_models
from src.modules.counterparties.infrastructure.database import models as counterparties_models
from src.modules.officials.infrastructure.database import models as officials_models
from src.modules.reports.infrastructure.database import models as reports_models
from src.modules.risk.infrastructure.database import models as risk_models

_ = (
    auth_models,
    audit_log,
    appeals_models,
    counterparties_models,
    officials_models,
    reports_models,
    risk_models,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", get_settings_from_env().database_url)

MODEL_SCHEMAS = {table.schema for table in target_metadata.tables.values() if table.schema}


def include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    if type_ == "schema":
        return name is None or name in MODEL_SCHEMAS
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
