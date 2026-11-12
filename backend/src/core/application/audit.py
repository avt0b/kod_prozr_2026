from uuid import UUID

from src.core.dto.page import Page, PageRequest
from src.core.infrastructure.interfaces.audit_log import AuditEntry, AuditLogInterface


class ListAuditLogUseCase:
    def __init__(self, repository: AuditLogInterface) -> None:
        self._repository = repository

    async def execute(self, object_id: UUID | None, page: PageRequest) -> Page[AuditEntry]:
        return await self._repository.list_entries(object_id, page.limit, page.offset)
