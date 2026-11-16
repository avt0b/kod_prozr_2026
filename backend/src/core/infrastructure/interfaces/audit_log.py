from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from src.core.dto.page import Page

AuditAction = Literal["open_profile", "create_report", "recompute_risk", "submit_appeal"]


@dataclass(frozen=True)
class AuditEntry:
    id: UUID
    actor: str
    action: str
    object_type: str
    object_id: UUID | None
    at: datetime


class AuditLogInterface(Protocol):
    async def record(
        self, action: AuditAction, object_type: str, object_id: UUID | None
    ) -> None: ...

    async def list_entries(
        self, object_id: UUID | None, limit: int, offset: int
    ) -> Page[AuditEntry]: ...
