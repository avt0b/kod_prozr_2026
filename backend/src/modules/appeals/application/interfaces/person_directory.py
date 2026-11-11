from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.appeals.application.dto.appeal_dto import PersonRef


class PersonDirectoryInterface(Protocol):
    """Что appeals нужно от officials: найти людей по фамилии и получить ФИО по id.

    Реализация — ACL-адаптер infrastructure/adapters/officials_acl.py, связка — src/web.
    """

    async def find_candidates(self, surname_stem: str) -> list[PersonRef]:
        """Люди, чьё ФИО содержит основу фамилии (без учёта регистра)."""
        ...

    async def get_many(self, person_ids: Sequence[UUID]) -> list[PersonRef]: ...
