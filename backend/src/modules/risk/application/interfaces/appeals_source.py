from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.risk.domain.facts import AppealMentionFacts


class AppealsSourceInterface(Protocol):
    async def mentions(self, person_ids: Sequence[UUID]) -> list[AppealMentionFacts]:
        """Упоминания служащих в обращениях (по linked_person_ids обращения)."""
        ...
