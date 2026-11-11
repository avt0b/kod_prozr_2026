from dataclasses import dataclass, field
from uuid import UUID

from src.core.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AppealAnalyzedEvent(DomainEvent):
    """Обращение проанализировано (создано или переанализировано).

    Подписчик в src/web/event_handlers.py пересчитывает риск (R07) затронутых людей:
    привязанных сейчас и отвязанных повторным анализом (ADR-10).
    """

    appeal_id: UUID
    is_corruption: bool
    linked_person_ids: tuple[UUID, ...] = field(default_factory=tuple)
    unlinked_person_ids: tuple[UUID, ...] = field(default_factory=tuple)

    @property
    def affected_person_ids(self) -> tuple[UUID, ...]:
        return tuple(dict.fromkeys(self.linked_person_ids + self.unlinked_person_ids))
