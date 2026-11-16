from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dto import Page, PageRequest
from src.core.infrastructure.database.upsert import upsert_rows
from src.modules.appeals.application.interfaces.appeal_repository import (
    AppealRepositoryInterface,
)
from src.modules.appeals.domain.appeal import Appeal
from src.modules.appeals.domain.enums import AppealCategory, AppealStatus, EntityType
from src.modules.appeals.domain.repeats import PriorAppeal, company_keys
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

    async def prior_subjects(
        self,
        exclude_id: UUID,
        since: datetime,
        before: datetime,
        person_ids: Sequence[UUID],
        with_companies: bool,
    ) -> list[PriorAppeal]:
        subjects = []
        if person_ids:
            subjects.append(AppealModel.linked_person_ids.overlap(list(person_ids)))
        if with_companies:
            organization = {"entities": [{"type": EntityType.ORGANIZATION.value}]}
            subjects.append(AppealModel.analysis.contains(organization))
        if not subjects:
            return []
        rows = await self._session.scalars(
            select(AppealModel)
            .where(
                AppealModel.id != exclude_id,
                AppealModel.analysis.is_not(None),
                AppealModel.received_at >= since,
                AppealModel.received_at < before,
                or_(*subjects),
            )
            .order_by(AppealModel.received_at.desc())
            .limit(MAX_LINKED)
        )
        result = []
        for row in rows:
            appeal = row.to_entity()
            result.append(
                PriorAppeal(
                    id=appeal.id,
                    received_at=appeal.received_at,
                    linked_person_ids=appeal.linked_person_ids,
                    companies=company_keys(appeal.analysis),
                )
            )
        return result

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
