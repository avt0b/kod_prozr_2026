from types import TracebackType
from typing import Protocol, Self


class UnitOfWorkInterface(Protocol):
    """Изменения репозиториев одной сессии фиксируются только commit().

    Выход из `async with` без commit() откатывает незафиксированные изменения.
    """

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
