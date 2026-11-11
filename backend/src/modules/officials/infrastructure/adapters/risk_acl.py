"""ACL officials -> risk. Модуль risk не импортируется: внешний источник описан локальным
протоколом, реальный объект (QueryRiskUseCase контекста risk) подставляет src/web."""

from collections import defaultdict
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.officials.application.dto.officials_dto import OfficialRiskDTO, RiskFlagView
from src.modules.officials.application.interfaces.risk_source import RiskSourceInterface


class ExternalRiskFlag(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def person_id(self) -> UUID: ...
    @property
    def rule_code(self) -> str: ...
    @property
    def rule_name(self) -> str: ...
    @property
    def severity(self) -> str: ...
    @property
    def weight(self) -> float: ...
    @property
    def explanation(self) -> str: ...
    @property
    def legal_ref(self) -> str | None: ...


class ExternalRiskScore(Protocol):
    @property
    def person_id(self) -> UUID: ...
    @property
    def score(self) -> float: ...


class ExternalRiskSource(Protocol):
    async def get_scores(self, person_ids: Sequence[UUID]) -> Sequence[ExternalRiskScore]: ...

    async def get_flags(self, person_ids: Sequence[UUID]) -> Sequence[ExternalRiskFlag]: ...


def _to_view(flag: ExternalRiskFlag) -> RiskFlagView:
    return RiskFlagView(
        id=flag.id,
        rule_code=flag.rule_code,
        rule_name=flag.rule_name,
        severity=flag.severity,
        weight=flag.weight,
        explanation=flag.explanation,
        legal_ref=flag.legal_ref,
    )


def _by_weight(flags: Sequence[ExternalRiskFlag]) -> list[ExternalRiskFlag]:
    return sorted(flags, key=lambda f: f.weight, reverse=True)


class RiskACLAdapter(RiskSourceInterface):
    def __init__(self, external_source: ExternalRiskSource) -> None:
        self._source = external_source

    async def get_scores(self, person_ids: Sequence[UUID]) -> dict[UUID, float]:
        return {s.person_id: s.score for s in await self._source.get_scores(person_ids)}

    async def get_top_flags(
        self, person_ids: Sequence[UUID], per_person: int
    ) -> dict[UUID, tuple[RiskFlagView, ...]]:
        grouped: dict[UUID, list[ExternalRiskFlag]] = defaultdict(list)
        for flag in await self._source.get_flags(person_ids):
            grouped[flag.person_id].append(flag)
        return {
            person_id: tuple(_to_view(f) for f in _by_weight(flags)[:per_person])
            for person_id, flags in grouped.items()
        }

    async def get_official_risk(self, person_id: UUID) -> OfficialRiskDTO:
        scores = await self._source.get_scores([person_id])
        flags = await self._source.get_flags([person_id])
        return OfficialRiskDTO(
            score=scores[0].score if scores else 0.0,
            flags=tuple(_to_view(f) for f in _by_weight(flags)),
        )
