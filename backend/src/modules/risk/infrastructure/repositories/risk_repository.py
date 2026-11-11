from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, distinct, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.database.upsert import UPSERT_CHUNK
from src.core.utils.iterables import chunked
from src.modules.risk.application.interfaces.risk_repository import RiskRepositoryInterface
from src.modules.risk.domain.flag import RiskFlag
from src.modules.risk.domain.score import RiskScore
from src.modules.risk.infrastructure.database.models import RiskFlagModel, RiskScoreModel


class RiskRepository(RiskRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_all(self, flags: list[RiskFlag], scores: list[RiskScore]) -> None:
        await self._session.execute(delete(RiskFlagModel))
        await self._session.execute(delete(RiskScoreModel))
        await self._insert(flags, scores)

    async def replace_for_persons(
        self, person_ids: Sequence[UUID], flags: list[RiskFlag], scores: list[RiskScore]
    ) -> None:
        for batch in chunked(person_ids):
            ids = list(batch)
            await self._session.execute(
                delete(RiskFlagModel).where(RiskFlagModel.person_id.in_(ids))
            )
            await self._session.execute(
                delete(RiskScoreModel).where(RiskScoreModel.person_id.in_(ids))
            )
        await self._insert(flags, scores)

    async def _insert(self, flags: list[RiskFlag], scores: list[RiskScore]) -> None:
        flag_rows = [RiskFlagModel.row(f) for f in flags]
        for batch in chunked(flag_rows, UPSERT_CHUNK):
            await self._session.execute(insert(RiskFlagModel), list(batch))
        score_rows = [RiskScoreModel.row(s) for s in scores]
        for batch in chunked(score_rows, UPSERT_CHUNK):
            await self._session.execute(insert(RiskScoreModel), list(batch))

    async def get_scores(self, person_ids: Sequence[UUID]) -> list[RiskScore]:
        result: list[RiskScore] = []
        for batch in chunked(person_ids):
            rows = await self._session.scalars(
                select(RiskScoreModel).where(RiskScoreModel.person_id.in_(list(batch)))
            )
            result.extend(r.to_entity() for r in rows)
        return result

    async def get_flags(self, person_ids: Sequence[UUID]) -> list[RiskFlag]:
        result: list[RiskFlag] = []
        for batch in chunked(person_ids):
            rows = await self._session.scalars(
                select(RiskFlagModel)
                .where(RiskFlagModel.person_id.in_(list(batch)))
                .order_by(RiskFlagModel.weight.desc(), RiskFlagModel.rule_code)
            )
            result.extend(r.to_entity() for r in rows)
        return result

    async def severity_counts(self) -> dict[str, int]:
        rows = await self._session.execute(
            select(RiskFlagModel.severity, func.count()).group_by(RiskFlagModel.severity)
        )
        counts = {"low": 0, "medium": 0, "high": 0}
        counts.update({severity: count for severity, count in rows.tuples()})
        return counts

    async def flagged_officials_count(self) -> int:
        total = await self._session.scalar(select(func.count(distinct(RiskFlagModel.person_id))))
        return total or 0
