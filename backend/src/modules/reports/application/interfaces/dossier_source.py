from typing import Protocol
from uuid import UUID

from src.modules.reports.domain.dossier import Dossier


class DossierSourceInterface(Protocol):
    """Что reports нужно от officials и risk. Реализация — ACL, связка — src/web."""

    async def get_dossier(self, person_id: UUID) -> Dossier | None:
        """None — человека нет или он не служащий."""
        ...
