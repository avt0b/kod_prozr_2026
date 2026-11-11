from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.core.dto import Page, PageRequest
from src.modules.appeals.domain.appeal import Appeal
from src.modules.appeals.domain.enums import AppealCategory, AppealStatus


class AppealRepositoryInterface(Protocol):
    async def get(self, appeal_id: UUID) -> Appeal | None: ...

    async def save(self, appeal: Appeal) -> None:
        """Вставить или обновить. Не коммитит."""
        ...

    async def upsert_many(self, appeals: Sequence[Appeal]) -> None: ...

    async def list_page(
        self,
        page: PageRequest,
        status: AppealStatus | None = None,
        category: AppealCategory | None = None,
    ) -> Page[Appeal]:
        """Новые сверху (received_at desc)."""
        ...

    async def linked_to(self, person_ids: Sequence[UUID]) -> list[Appeal]:
        """Обращения, где среди linked_person_ids есть кто-то из person_ids."""
        ...

    async def list_unanalyzed(self, limit: int) -> list[Appeal]: ...

    async def status_counts(self) -> dict[str, int]: ...
