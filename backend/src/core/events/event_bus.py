from typing import Protocol

from src.core.events.base import DomainEvent


class EventBus(Protocol):
    """Порт шины доменных событий. Публикуется ПОСЛЕ коммита Unit of Work."""

    async def publish(self, event: DomainEvent) -> None: ...

    async def publish_all(self, events: list[DomainEvent]) -> None: ...
