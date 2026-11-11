from collections import defaultdict
from collections.abc import Awaitable, Callable

from src.core.events.base import DomainEvent
from src.core.events.event_bus import EventBus
from src.core.infrastructure.logger import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class InMemoryEventBus(EventBus):
    """Шина событий внутри процесса. В optimus на этом месте NATS — нам он не нужен.

    Подписки регистрирует composition root (src/web/create_app.py). Ошибка подписчика
    логируется и не валит публикующий use case: событие публикуется после коммита.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            try:
                await handler(event)
            except Exception:
                logger.exception("Event handler failed for {}", type(event).__name__)

    async def publish_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)
