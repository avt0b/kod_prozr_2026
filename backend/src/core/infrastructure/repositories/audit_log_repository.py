from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dto.page import Page
from src.core.infrastructure.database.models.audit_log import AuditLogModel
from src.core.infrastructure.interfaces.audit_log import AuditAction, AuditEntry


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, action: AuditAction, object_type: str, object_id: UUID | None) -> None:
        self._session.add(
            AuditLogModel(
                actor="analyst", action=action, object_type=object_type, object_id=object_id
            )
        )

    async def list_entries(
        self, object_id: UUID | None, limit: int, offset: int
    ) -> Page[AuditEntry]:
        stmt = select(AuditLogModel)
        if object_id is not None:
            stmt = stmt.where(AuditLogModel.object_id == object_id)
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = await self._session.scalars(
            stmt.order_by(AuditLogModel.at.desc(), AuditLogModel.id).limit(limit).offset(offset)
        )
        return Page(
            items=[
                AuditEntry(r.id, r.actor, r.action, r.object_type, r.object_id, r.at) for r in rows
            ],
            total=total or 0,
        )
