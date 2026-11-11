from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

_UOW_ACTIVE = "unit_of_work_active"


class SqlAlchemyUnitOfWork:
    """Транзакцией владеет use case. Выход из блока без commit() откатывает изменения."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> Self:
        if self._session.info.get(_UOW_ACTIVE):
            raise RuntimeError("Nested unit of work is not supported")
        self._session.info[_UOW_ACTIVE] = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            await self.rollback()  # no-op после commit()
        finally:
            self._session.info.pop(_UOW_ACTIVE, None)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
