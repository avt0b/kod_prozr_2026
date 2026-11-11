from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def get_engine(db_url: str, echo: bool = False) -> AsyncEngine:
    return create_async_engine(db_url, echo=echo, pool_pre_ping=True, pool_size=10, max_overflow=20)


def get_async_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
