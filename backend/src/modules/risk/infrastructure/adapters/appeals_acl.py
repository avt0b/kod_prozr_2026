"""ACL risk -> appeals: упоминания служащих в обращениях (для R07 и графа)."""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.risk.application.interfaces.appeals_source import AppealsSourceInterface
from src.modules.risk.domain.facts import AppealMentionFacts


class ExternalMention(Protocol):
    @property
    def appeal_id(self) -> UUID: ...
    @property
    def person_id(self) -> UUID: ...
    @property
    def is_corruption(self) -> bool: ...
    @property
    def category(self) -> str | None: ...
    @property
    def specificity(self) -> float: ...
    @property
    def confidence(self) -> float: ...
    @property
    def received_at(self) -> datetime: ...
    @property
    def summary(self) -> str | None: ...


class ExternalAppealsSource(Protocol):
    async def mentions(self, person_ids: Sequence[UUID]) -> Sequence[ExternalMention]: ...


class AppealsACLAdapter(AppealsSourceInterface):
    def __init__(self, external_source: ExternalAppealsSource) -> None:
        self._source = external_source

    async def mentions(self, person_ids: Sequence[UUID]) -> list[AppealMentionFacts]:
        return [
            AppealMentionFacts(
                appeal_id=m.appeal_id,
                person_id=m.person_id,
                is_corruption=m.is_corruption,
                category=m.category,
                specificity=m.specificity,
                confidence=m.confidence,
                received_at=m.received_at.date(),
                summary=m.summary,
            )
            for m in await self._source.mentions(person_ids)
        ]
