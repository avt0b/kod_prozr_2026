"""ACL карты рисков: stats -> officials (текущие должности) и stats -> risk (баллы, флаги).

Внешние источники — локальные протоколы; настоящие Query*UseCase модулей подставляет
src/web/wiring.py.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.stats.application.interfaces.risk_map_sources import (
    OfficialPlacement,
    OfficialPlacementsInterface,
    OfficialRiskProfilesInterface,
    OfficialRiskView,
    PositionView,
)


class ExternalOrgan(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def name(self) -> str: ...


class ExternalPosition(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def title(self) -> str: ...
    @property
    def department(self) -> str: ...
    @property
    def is_corruption_risky(self) -> bool: ...


class ExternalAuthority(Protocol):
    @property
    def kind(self) -> str: ...


class ExternalAppointment(Protocol):
    @property
    def position(self) -> ExternalPosition: ...
    @property
    def organ(self) -> ExternalOrgan: ...
    @property
    def authorities(self) -> Sequence[ExternalAuthority]: ...


class ExternalPerson(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def full_name(self) -> str: ...


class ExternalSnapshot(Protocol):
    @property
    def person(self) -> ExternalPerson: ...
    @property
    def current_appointment(self) -> ExternalAppointment | None: ...


class ExternalOfficialsSource(Protocol):
    async def official_ids(self) -> list[UUID]: ...

    async def snapshots(self, person_ids: Sequence[UUID]) -> Sequence[ExternalSnapshot]: ...


class ExternalScore(Protocol):
    @property
    def person_id(self) -> UUID: ...
    @property
    def score(self) -> float: ...


class ExternalFlag(Protocol):
    @property
    def person_id(self) -> UUID: ...
    @property
    def rule_code(self) -> str: ...


class ExternalRiskStats(Protocol):
    @property
    def computed_at(self) -> datetime | None: ...


class ExternalRiskSource(Protocol):
    async def get_scores(self, person_ids: Sequence[UUID]) -> Sequence[ExternalScore]: ...

    async def get_flags(self, person_ids: Sequence[UUID]) -> Sequence[ExternalFlag]: ...

    async def stats(self) -> ExternalRiskStats: ...


class OfficialPlacementsACLAdapter(OfficialPlacementsInterface):
    def __init__(self, source: ExternalOfficialsSource) -> None:
        self._source = source

    async def placements(self) -> list[OfficialPlacement]:
        snapshots = await self._source.snapshots(await self._source.official_ids())
        result: list[OfficialPlacement] = []
        for snapshot in snapshots:
            current = snapshot.current_appointment
            if current is None:
                continue
            result.append(
                OfficialPlacement(
                    person_id=snapshot.person.id,
                    full_name=snapshot.person.full_name,
                    position=PositionView(
                        id=current.position.id,
                        title=current.position.title,
                        department=current.position.department,
                        organ_id=current.organ.id,
                        organ_name=current.organ.name,
                        is_corruption_risky=current.position.is_corruption_risky,
                        authority_kinds=tuple(dict.fromkeys(a.kind for a in current.authorities)),
                    ),
                )
            )
        return result


class OfficialRiskProfilesACLAdapter(OfficialRiskProfilesInterface):
    def __init__(self, source: ExternalRiskSource) -> None:
        self._source = source

    async def risk_profiles(self, person_ids: Sequence[UUID]) -> dict[UUID, OfficialRiskView]:
        if not person_ids:
            return {}
        scores = {s.person_id: s.score for s in await self._source.get_scores(person_ids)}
        rules: dict[UUID, list[str]] = {}
        for flag in await self._source.get_flags(person_ids):
            rules.setdefault(flag.person_id, []).append(flag.rule_code)
        return {
            pid: OfficialRiskView(
                person_id=pid,
                score=scores.get(pid, 0.0),
                rule_codes=tuple(dict.fromkeys(rules.get(pid, ()))),
            )
            for pid in person_ids
            if pid in scores or pid in rules
        }

    async def computed_at(self) -> datetime | None:
        return (await self._source.stats()).computed_at
