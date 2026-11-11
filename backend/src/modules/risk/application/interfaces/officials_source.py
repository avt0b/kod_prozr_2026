from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.risk.domain.facts import OfficialFacts, OrganFacts, PersonFacts, RelativeLinkFacts


class OfficialsSourceInterface(Protocol):
    """Что risk нужно от контекста officials (в терминах risk). Реализация — ACL-адаптер."""

    async def official_ids(self) -> list[UUID]: ...

    async def officials(self, person_ids: Sequence[UUID]) -> list[OfficialFacts]:
        """Только служащие (с назначениями); прочие id молча пропускаются."""
        ...

    async def persons(self, person_ids: Sequence[UUID]) -> list[PersonFacts]: ...

    async def relatives(self, person_ids: Sequence[UUID]) -> list[RelativeLinkFacts]: ...

    async def organs(self, organ_ids: Sequence[UUID]) -> list[OrganFacts]: ...
