from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from src.core.dto import Page, PageRequest
from src.modules.officials.application.dto.officials_dto import OfficialListItemDTO, RiskScoreView
from src.modules.officials.application.interfaces.appointment_repository import (
    AppointmentRepositoryInterface,
)
from src.modules.officials.application.interfaces.risk_source import RiskSourceInterface
from src.modules.officials.application.use_cases.get_official_snapshots import (
    GetOfficialSnapshotsUseCase,
)

# Рейтинг сортируется по баллу из другого контекста, поэтому кандидатов фильтруем здесь,
# а баллы берём пачкой через ACL. Для объёма хакатона (тысячи служащих) этого достаточно;
# при росте — read-модель рейтинга (как projector в optimus).
MAX_RATING_CANDIDATES = 50_000
TOP_FLAGS = 3
_NO_SCORE = RiskScoreView(score=0.0, flags_count=0)


class OfficialsSort(StrEnum):
    RISK_DESC = "-risk_score"
    RISK_ASC = "risk_score"
    NAME_ASC = "full_name"
    NAME_DESC = "-full_name"


@dataclass(frozen=True)
class OfficialsFilter:
    query: str | None = None
    organ_id: UUID | None = None
    min_score: float | None = None
    sort: OfficialsSort = OfficialsSort.RISK_DESC


class ListOfficialsUseCase:
    def __init__(
        self,
        appointment_repository: AppointmentRepositoryInterface,
        snapshots: GetOfficialSnapshotsUseCase,
        risk_source: RiskSourceInterface,
    ) -> None:
        self._appointments = appointment_repository
        self._snapshots = snapshots
        self._risk = risk_source

    async def execute(
        self, filters: OfficialsFilter, page: PageRequest
    ) -> Page[OfficialListItemDTO]:
        # id уже отсортированы по ФИО — это вторичный ключ сортировки по баллу.
        candidate_ids = await self._appointments.search_official_ids(
            filters.query, filters.organ_id, MAX_RATING_CANDIDATES
        )
        scores = await self._risk.get_scores(candidate_ids)

        def score(person_id: UUID) -> float:
            return scores.get(person_id, _NO_SCORE).score

        def rank(person_id: UUID) -> tuple[float, int]:
            # При равном балле выше тот, у кого больше флагов (contracts.md).
            found = scores.get(person_id, _NO_SCORE)
            return found.score, found.flags_count

        ids = candidate_ids
        if filters.min_score is not None:
            ids = [pid for pid in ids if score(pid) >= filters.min_score]
        # sorted стабилен и при reverse=True: при равенстве остаётся порядок по ФИО.
        if filters.sort is OfficialsSort.RISK_DESC:
            ids = sorted(ids, key=rank, reverse=True)
        elif filters.sort is OfficialsSort.RISK_ASC:
            ids = sorted(ids, key=rank)
        elif filters.sort is OfficialsSort.NAME_DESC:
            ids = list(reversed(ids))

        page_ids = ids[page.offset : page.offset + page.limit]
        snapshots = {s.person.id: s for s in await self._snapshots.execute(page_ids)}
        top_flags = await self._risk.get_top_flags(page_ids, TOP_FLAGS)

        items: list[OfficialListItemDTO] = []
        for person_id in page_ids:
            snapshot = snapshots.get(person_id)
            if snapshot is None:
                continue
            current = snapshot.current_appointment
            items.append(
                OfficialListItemDTO(
                    id=person_id,
                    full_name=snapshot.person.full_name,
                    position=current.position if current else None,
                    organ=current.organ if current else None,
                    risk_score=score(person_id),
                    top_flags=top_flags.get(person_id, ()),
                )
            )
        return Page(items=items, total=len(ids))
