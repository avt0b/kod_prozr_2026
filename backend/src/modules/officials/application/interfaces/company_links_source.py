from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.officials.application.dto.officials_dto import (
    CompanyRoleView,
    CompanyView,
    ContractView,
)


class CompanyLinksSourceInterface(Protocol):
    """Что officials нужно от counterparties для профиля."""

    async def get_roles(self, person_ids: Sequence[UUID]) -> list[CompanyRoleView]:
        """Роли учредителя и директора людей person_ids, с данными компаний."""
        ...

    async def get_companies(self, company_ids: Sequence[UUID]) -> list[CompanyView]: ...

    async def contracts(
        self, organ_ids: Sequence[UUID], company_ids: Sequence[UUID]
    ) -> list[ContractView]:
        """Контракты компаний company_ids с органами organ_ids."""
        ...
