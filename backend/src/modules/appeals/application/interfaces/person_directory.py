from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.appeals.application.dto.appeal_dto import PersonRef
from src.modules.appeals.application.interfaces.person_matcher import OfficialCard


class PersonDirectoryInterface(Protocol):
    """Что appeals нужно от officials: справочник служащих с должностями и ФИО по id.

    Реализация — ACL-адаптер infrastructure/adapters/officials_acl.py, связка — src/web.
    """

    async def officials(self) -> list[OfficialCard]:
        """Все служащие (с назначениями, включая прошлые) — вход сопоставления лиц (AI-05)."""
        ...

    async def get_many(self, person_ids: Sequence[UUID]) -> list[PersonRef]: ...
