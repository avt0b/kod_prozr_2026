"""ACL risk -> officials. Переводит «снимок служащего» officials в факты risk."""

from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from src.modules.risk.application.interfaces.officials_source import OfficialsSourceInterface
from src.modules.risk.domain.facts import (
    AppointmentFacts,
    AuthorityFacts,
    EmploymentFacts,
    OfficialFacts,
    OrganFacts,
    PersonFacts,
    RelativeFacts,
    RelativeLinkFacts,
)


class ExternalPerson(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def full_name(self) -> str: ...
    @property
    def address(self) -> str | None: ...
    @property
    def phone(self) -> str | None: ...


class ExternalOrgan(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def name(self) -> str: ...
    @property
    def region(self) -> str: ...


class ExternalPosition(Protocol):
    @property
    def title(self) -> str: ...


class ExternalAuthority(Protocol):
    @property
    def kind(self) -> str: ...
    @property
    def okpd2(self) -> Sequence[str]: ...


class ExternalAppointment(Protocol):
    @property
    def organ(self) -> ExternalOrgan: ...
    @property
    def position(self) -> ExternalPosition: ...
    @property
    def started_at(self) -> date: ...
    @property
    def ended_at(self) -> date | None: ...
    @property
    def authorities(self) -> Sequence[ExternalAuthority]: ...


class ExternalRelative(Protocol):
    @property
    def person_id(self) -> UUID: ...
    @property
    def kind(self) -> str: ...
    @property
    def person(self) -> ExternalPerson: ...


class ExternalEmployment(Protocol):
    @property
    def company_id(self) -> UUID: ...
    @property
    def started_at(self) -> date: ...
    @property
    def ended_at(self) -> date | None: ...


class ExternalSnapshot(Protocol):
    @property
    def person(self) -> ExternalPerson: ...
    @property
    def appointments(self) -> Sequence[ExternalAppointment]: ...
    @property
    def relatives(self) -> Sequence[ExternalRelative]: ...
    @property
    def employments(self) -> Sequence[ExternalEmployment]: ...


class ExternalOfficialsSource(Protocol):
    async def official_ids(self) -> list[UUID]: ...

    async def snapshots(self, person_ids: Sequence[UUID]) -> Sequence[ExternalSnapshot]: ...

    async def persons(self, person_ids: Sequence[UUID]) -> Sequence[ExternalPerson]: ...

    async def relatives(self, person_ids: Sequence[UUID]) -> Sequence[ExternalRelative]: ...

    async def organs(self, organ_ids: Sequence[UUID]) -> Sequence[ExternalOrgan]: ...


def _person(person: ExternalPerson) -> PersonFacts:
    return PersonFacts(
        id=person.id, full_name=person.full_name, address=person.address, phone=person.phone
    )


def _official(snapshot: ExternalSnapshot) -> OfficialFacts:
    return OfficialFacts(
        person=_person(snapshot.person),
        appointments=tuple(
            AppointmentFacts(
                organ_id=a.organ.id,
                organ_name=a.organ.name,
                position_title=a.position.title,
                started_at=a.started_at,
                ended_at=a.ended_at,
                authorities=tuple(
                    AuthorityFacts(kind=x.kind, okpd2=tuple(x.okpd2)) for x in a.authorities
                ),
                organ_region=a.organ.region,
            )
            for a in snapshot.appointments
        ),
        relatives=tuple(
            RelativeFacts(person=_person(r.person), kind=r.kind) for r in snapshot.relatives
        ),
        employments=tuple(
            EmploymentFacts(company_id=e.company_id, started_at=e.started_at, ended_at=e.ended_at)
            for e in snapshot.employments
        ),
    )


class OfficialsACLAdapter(OfficialsSourceInterface):
    def __init__(self, external_source: ExternalOfficialsSource) -> None:
        self._source = external_source

    async def official_ids(self) -> list[UUID]:
        return await self._source.official_ids()

    async def officials(self, person_ids: Sequence[UUID]) -> list[OfficialFacts]:
        return [_official(s) for s in await self._source.snapshots(person_ids)]

    async def persons(self, person_ids: Sequence[UUID]) -> list[PersonFacts]:
        return [_person(p) for p in await self._source.persons(person_ids)]

    async def relatives(self, person_ids: Sequence[UUID]) -> list[RelativeLinkFacts]:
        return [
            RelativeLinkFacts(person_id=r.person_id, relative=_person(r.person), kind=r.kind)
            for r in await self._source.relatives(person_ids)
        ]

    async def organs(self, organ_ids: Sequence[UUID]) -> list[OrganFacts]:
        return [OrganFacts(id=o.id, name=o.name) for o in await self._source.organs(organ_ids)]
