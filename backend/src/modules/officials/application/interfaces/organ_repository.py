from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.core.dto import Page, PageRequest
from src.modules.officials.domain.organ import Authority, Organ, Position


class OrganRepositoryInterface(Protocol):
    """Органы, их должности и полномочия должностей."""

    async def list_page(self, page: PageRequest) -> Page[Organ]: ...

    async def get_many(self, organ_ids: Sequence[UUID]) -> list[Organ]: ...

    async def get_positions(self, position_ids: Sequence[UUID]) -> list[Position]: ...

    async def get_authorities(self, position_ids: Sequence[UUID]) -> list[Authority]: ...

    async def upsert_many(
        self, organs: list[Organ], positions: list[Position], authorities: list[Authority]
    ) -> None:
        """Вставить или обновить по id. Не коммитит."""
        ...
