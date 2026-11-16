"""ACL appeals -> officials: справочник служащих с должностями и ФИО по id.

Модуль officials не импортируется: внешний источник описан локальным протоколом,
настоящий объект (QueryOfficialsUseCase) подставляет src/web/dependencies.py.
"""

from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from src.modules.appeals.application.dto.appeal_dto import PersonRef
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface
from src.modules.appeals.application.interfaces.person_matcher import OfficialCard, OfficialPost


class ExternalPerson(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def full_name(self) -> str: ...


class ExternalTitle(Protocol):
    @property
    def title(self) -> str: ...

    @property
    def department(self) -> str: ...


class ExternalOrgan(Protocol):
    @property
    def name(self) -> str: ...


class ExternalAppointment(Protocol):
    @property
    def position(self) -> ExternalTitle: ...
    @property
    def organ(self) -> ExternalOrgan: ...
    @property
    def started_at(self) -> date: ...
    @property
    def ended_at(self) -> date | None: ...


class ExternalSnapshot(Protocol):
    @property
    def person(self) -> ExternalPerson: ...
    @property
    def current_appointment(self) -> ExternalAppointment | None: ...

    @property
    def appointments(self) -> Sequence[ExternalAppointment]: ...


class ExternalScore(Protocol):
    @property
    def person_id(self) -> UUID: ...
    @property
    def score(self) -> float: ...


class ExternalRiskSource(Protocol):
    async def get_scores(self, person_ids: Sequence[UUID]) -> Sequence[ExternalScore]: ...


class ExternalPersonSource(Protocol):
    async def official_ids(self) -> Sequence[UUID]: ...

    async def persons(self, person_ids: Sequence[UUID]) -> Sequence[ExternalPerson]: ...

    async def snapshots(self, person_ids: Sequence[UUID]) -> Sequence[ExternalSnapshot]: ...


class OfficialsDirectoryACLAdapter(PersonDirectoryInterface):
    def __init__(self, external_source: ExternalPersonSource, risk: ExternalRiskSource) -> None:
        self._source = external_source
        self._risk = risk

    async def officials(self) -> list[OfficialCard]:
        snapshots = await self._source.snapshots(list(await self._source.official_ids()))
        return [
            OfficialCard(
                id=s.person.id,
                full_name=s.person.full_name,
                posts=tuple(
                    OfficialPost(
                        title=a.position.title,
                        department=a.position.department,
                        organ=a.organ.name,
                        started_at=a.started_at,
                        ended_at=a.ended_at,
                    )
                    for a in s.appointments
                ),
            )
            for s in snapshots
        ]

    async def get_many(self, person_ids: Sequence[UUID]) -> list[PersonRef]:
        if not person_ids:
            return []
        snapshots = await self._source.snapshots(list(person_ids))
        scores = {s.person_id: s.score for s in await self._risk.get_scores(person_ids)}
        return [
            PersonRef(
                id=s.person.id,
                full_name=s.person.full_name,
                position=s.current_appointment.position.title if s.current_appointment else None,
                organ=s.current_appointment.organ.name if s.current_appointment else None,
                risk_score=scores.get(s.person.id, 0.0),
            )
            for s in snapshots
        ]
