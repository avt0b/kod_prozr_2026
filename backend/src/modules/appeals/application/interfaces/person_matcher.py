from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from src.modules.appeals.domain.analysis import AppealAnalysis, MatchCandidate


@dataclass(frozen=True)
class OfficialPost:
    """Должность служащего глазами appeals: для сверки с упомянутой должностью и органом."""

    title: str
    department: str
    organ: str
    started_at: date
    ended_at: date | None

    def held_on(self, day: date) -> bool:
        return self.started_at <= day and (self.ended_at is None or day <= self.ended_at)


@dataclass(frozen=True)
class OfficialCard:
    id: UUID
    full_name: str
    posts: tuple[OfficialPost, ...]


@dataclass(frozen=True)
class MatchResult:
    linked: tuple[UUID, ...]
    candidates: tuple[MatchCandidate, ...]


class PersonMatcherInterface(Protocol):
    """Сопоставление упомянутых лиц с профилями служащих (AI-05, ai.md §3).

    linked — автоматическая привязка (балл ≥ 0.8 и кандидат единственный);
    candidates — «возможно: …» для подтверждения аналитиком (однофамильцы, только должность).
    Реализация — infrastructure/adapters/person_matcher.py.
    """

    def match(
        self,
        analysis: AppealAnalysis,
        text: str,
        officials: Sequence[OfficialCard],
        on: date,
    ) -> MatchResult: ...
