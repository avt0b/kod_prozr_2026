from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.officials.application.dto.officials_dto import CompanyLinkView


class CompanyLinksSourceInterface(Protocol):
    """Что officials нужно от counterparties: компании, где человек учредитель/руководитель."""

    async def get_links(self, person_ids: Sequence[UUID]) -> list[CompanyLinkView]: ...
