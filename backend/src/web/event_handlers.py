"""Подписчики доменных событий (in-process шина). Здесь — потому что связывают контексты."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.events.base import DomainEvent
from src.core.infrastructure.events import InMemoryEventBus
from src.core.infrastructure.logger import get_logger
from src.modules.appeals.domain.events import AppealAnalyzedEvent
from src.web import wiring

logger = get_logger(__name__)


def register_event_handlers(
    bus: InMemoryEventBus, session_maker: async_sessionmaker[AsyncSession]
) -> None:
    async def recompute_risk_on_appeal(event: DomainEvent) -> None:
        """ADR-10: после анализа обращения синхронно пересчитать риск затронутых людей.

        Шина вызывает подписчика до ответа на POST /appeals, поэтому фронт сразу видит
        новый балл. Своя сессия: транзакция обращения уже закоммичена.
        """
        if not isinstance(event, AppealAnalyzedEvent) or not event.affected_person_ids:
            return
        async with session_maker() as session:
            result = await wiring.recompute_risk_use_case(session).execute(
                event.affected_person_ids
            )
        logger.info(
            "Risk recomputed after appeal {}: {} officials",
            event.appeal_id,
            result.officials_processed,
        )

    bus.subscribe(AppealAnalyzedEvent, recompute_risk_on_appeal)
