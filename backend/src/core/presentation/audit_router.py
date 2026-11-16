from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.application.audit import ListAuditLogUseCase
from src.core.dto.page import MAX_PAGE_LIMIT, PageRequest
from src.core.infrastructure.dependencies import get_audit_log
from src.core.infrastructure.interfaces.audit_log import AuditLogInterface
from src.core.schemas import APIModel, PageResponse

router = APIRouter(tags=["Audit"])


class AuditEntryResponse(APIModel):
    id: UUID
    actor: str
    action: str
    object_type: str
    object_id: UUID | None
    at: datetime


@router.get("/audit", response_model=PageResponse[AuditEntryResponse])
async def list_audit(
    repository: Annotated[AuditLogInterface, Depends(get_audit_log)],
    object_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[AuditEntryResponse]:
    page = await ListAuditLogUseCase(repository).execute(object_id, PageRequest(limit, offset))
    return PageResponse(
        items=[AuditEntryResponse.model_validate(a) for a in page.items], total=page.total
    )
