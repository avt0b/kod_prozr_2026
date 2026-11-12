from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import Settings
from src.core.events.event_bus import EventBus
from src.core.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from src.core.infrastructure.interfaces.audit_log import AuditLogInterface
from src.core.infrastructure.interfaces.llm_client import LLMClientInterface
from src.core.infrastructure.interfaces.unit_of_work import UnitOfWorkInterface
from src.core.infrastructure.repositories.audit_log_repository import AuditLogRepository


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_maker: async_sessionmaker[AsyncSession] = request.app.state.session_maker
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_unit_of_work(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UnitOfWorkInterface:
    return SqlAlchemyUnitOfWork(session)


def get_event_bus(request: Request) -> EventBus:
    return cast(EventBus, request.app.state.event_bus)


def get_llm_client(request: Request) -> LLMClientInterface | None:
    """None, если LLM_BASE_URL не задан: модули тогда берут фейковые адаптеры."""
    return cast(LLMClientInterface | None, request.app.state.llm_client)


def get_audit_log(session: Annotated[AsyncSession, Depends(get_session)]) -> AuditLogInterface:
    return AuditLogRepository(session)
