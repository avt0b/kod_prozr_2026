from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.core.events.base import DomainEvent
from src.modules.appeals.domain.analysis import AppealAnalysis
from src.modules.appeals.domain.enums import AppealStatus
from src.modules.appeals.domain.events import AppealAnalyzedEvent
from src.modules.appeals.domain.exceptions import (
    AppealClosedError,
    EmptyAppealTextError,
    InvalidAppealStatusTransitionError,
)

MAX_TEXT_LENGTH = 20_000


class Appeal:
    """Обращение гражданина. Агрегат: статус меняется только через методы.

    new -> analyzed -> routed -> closed; повторный анализ разрешён до закрытия.
    """

    def __init__(
        self,
        text: str,
        channel: str,
        received_at: datetime | None = None,
        status: AppealStatus = AppealStatus.NEW,
        analysis: AppealAnalysis | None = None,
        linked_person_ids: tuple[UUID, ...] = (),
        id: UUID | None = None,
    ) -> None:
        cleaned = text.strip()
        if not cleaned:
            raise EmptyAppealTextError()
        self._id = id or uuid4()
        self._text = cleaned[:MAX_TEXT_LENGTH]
        self._channel = channel
        self._received_at = received_at or datetime.now(UTC)
        self._status = status
        self._analysis = analysis
        self._linked_person_ids = linked_person_ids
        self._domain_events: list[DomainEvent] = []

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def text(self) -> str:
        return self._text

    @property
    def channel(self) -> str:
        return self._channel

    @property
    def received_at(self) -> datetime:
        return self._received_at

    @property
    def status(self) -> AppealStatus:
        return self._status

    @property
    def analysis(self) -> AppealAnalysis | None:
        return self._analysis

    @property
    def linked_person_ids(self) -> tuple[UUID, ...]:
        return self._linked_person_ids

    @property
    def domain_events(self) -> list[DomainEvent]:
        return self._domain_events

    def apply_analysis(self, analysis: AppealAnalysis, linked_person_ids: tuple[UUID, ...]) -> None:
        if self._status is AppealStatus.CLOSED:
            raise AppealClosedError(self._id)
        previous = self._linked_person_ids
        self._analysis = analysis
        self._linked_person_ids = tuple(dict.fromkeys(linked_person_ids))
        if self._status is AppealStatus.NEW:
            self._status = AppealStatus.ANALYZED
        self._domain_events.append(
            AppealAnalyzedEvent(
                appeal_id=self._id,
                is_corruption=analysis.is_corruption,
                linked_person_ids=self._linked_person_ids,
                unlinked_person_ids=tuple(p for p in previous if p not in self._linked_person_ids),
            )
        )

    def route(self) -> None:
        if self._status is not AppealStatus.ANALYZED:
            raise InvalidAppealStatusTransitionError(self._status, AppealStatus.ROUTED)
        self._status = AppealStatus.ROUTED

    def close(self) -> None:
        if self._status is AppealStatus.CLOSED:
            raise AppealClosedError(self._id)
        self._status = AppealStatus.CLOSED

    def clear_events(self) -> None:
        self._domain_events.clear()
