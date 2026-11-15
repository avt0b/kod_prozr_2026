from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.core.dto import Page, PageRequest
from src.modules.appeals.domain.appeal import Appeal
from src.modules.appeals.domain.enums import AppealCategory, AppealStatus
from src.modules.appeals.domain.repeats import PriorAppeal


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

    async def prior_subjects(
        self,
        exclude_id: UUID,
        since: datetime,
        before: datetime,
        person_ids: Sequence[UUID],
        with_companies: bool,
    ) -> list[PriorAppeal]:
        """Разобранные обращения с received_at в [since, before), кроме exclude_id, где
        привязан кто-то из person_ids или (with_companies) названа организация. Сверку
        компаний по названию делает домен (repeats.find_repeats)."""
        ...

    async def list_unanalyzed(self, limit: int) -> list[Appeal]: ...

    async def status_counts(self) -> dict[str, int]: ...
