from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dto import Page, PageRequest
from src.core.infrastructure.database.upsert import upsert_rows
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.domain.appeal import Appeal
from src.modules.appeals.domain.enums import AppealCategory, AppealStatus
from src.modules.appeals.infrastructure.database.models import AppealModel

MAX_LINKED = 10_000


class AppealRepository(AppealRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, appeal_id: UUID) -> Appeal | None:
        model = await self._session.get(AppealModel, appeal_id)
        return model.to_entity() if model else None

    async def save(self, appeal: Appeal) -> None:
        await upsert_rows(self._session, AppealModel, [AppealModel.row(appeal)])

    async def upsert_many(self, appeals: Sequence[Appeal]) -> None:
        await upsert_rows(self._session, AppealModel, [AppealModel.row(a) for a in appeals])

    async def list_page(
        self,
        page: PageRequest,
        status: AppealStatus | None = None,
        category: AppealCategory | None = None,
    ) -> Page[Appeal]:
        stmt = select(AppealModel)
        if status is not None:
            stmt = stmt.where(AppealModel.status == status.value)
        if category is not None:
            stmt = stmt.where(AppealModel.category == category.value)
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = await self._session.scalars(
            stmt.order_by(AppealModel.received_at.desc()).limit(page.limit).offset(page.offset)
        )
        return Page(items=[r.to_entity() for r in rows], total=total or 0)

    async def linked_to(self, person_ids: Sequence[UUID]) -> list[Appeal]:
        if not person_ids:
            return []
        rows = await self._session.scalars(
            select(AppealModel)
            .where(AppealModel.linked_person_ids.overlap(list(person_ids)))
            .order_by(AppealModel.received_at.desc())
            .limit(MAX_LINKED)
        )
        return [r.to_entity() for r in rows]

    async def list_unanalyzed(self, limit: int) -> list[Appeal]:
        rows = await self._session.scalars(
            select(AppealModel)
            .where(AppealModel.analysis.is_(None))
            .order_by(AppealModel.received_at)
            .limit(limit)
        )
        return [r.to_entity() for r in rows]

    async def status_counts(self) -> dict[str, int]:
        rows = await self._session.execute(
            select(AppealModel.status, func.count()).group_by(AppealModel.status)
        )
        counts = {status.value: 0 for status in AppealStatus}
        counts.update({status: count for status, count in rows})
        return counts
