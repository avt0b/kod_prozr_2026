"""ACL appeals -> officials: поиск людей по фамилии и ФИО по id.

Модуль officials не импортируется: внешний источник описан локальным протоколом,
настоящий объект (QueryOfficialsUseCase) подставляет src/web/dependencies.py.
"""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.appeals.application.dto.appeal_dto import PersonRef
from src.modules.appeals.application.interfaces.person_directory import PersonDirectoryInterface


class ExternalPerson(Protocol):
    @property
    def id(self) -> UUID: ...
    @property
    def full_name(self) -> str: ...


class ExternalPersonSource(Protocol):
    async def persons_by_name(self, name_query: str) -> Sequence[ExternalPerson]: ...

    async def persons(self, person_ids: Sequence[UUID]) -> Sequence[ExternalPerson]: ...


class OfficialsDirectoryACLAdapter(PersonDirectoryInterface):
    def __init__(self, external_source: ExternalPersonSource) -> None:
        self._source = external_source

    async def find_candidates(self, surname_stem: str) -> list[PersonRef]:
        found = await self._source.persons_by_name(surname_stem)
        return [PersonRef(id=p.id, full_name=p.full_name) for p in found]

    async def get_many(self, person_ids: Sequence[UUID]) -> list[PersonRef]:
        if not person_ids:
            return []
        found = await self._source.persons(list(person_ids))
        return [PersonRef(id=p.id, full_name=p.full_name) for p in found]
