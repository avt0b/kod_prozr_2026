from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.core.dto import PageRequest
from src.core.dto.page import MAX_PAGE_LIMIT
from src.core.schemas import PageResponse
from src.modules.appeals.application.use_cases.change_appeal_status import (
    ChangeAppealStatusUseCase,
)
from src.modules.appeals.application.use_cases.create_appeal import CreateAppealUseCase
from src.modules.appeals.application.use_cases.get_appeal import GetAppealUseCase
from src.modules.appeals.application.use_cases.list_appeals import ListAppealsUseCase
from src.modules.appeals.application.use_cases.reanalyze_appeal import ReanalyzeAppealUseCase
from src.modules.appeals.domain.enums import AppealCategory, AppealStatus
from src.modules.appeals.presentation.dependencies import (
    get_change_appeal_status_use_case,
    get_create_appeal_use_case,
    get_get_appeal_use_case,
    get_list_appeals_use_case,
    get_reanalyze_appeal_use_case,
)
from src.modules.appeals.presentation.schemas.appeals import (
    AppealCreateRequest,
    AppealResponse,
    AppealStatusRequest,
)

router = APIRouter(tags=["Appeals"])


@router.get("/appeals", response_model=PageResponse[AppealResponse])
async def list_appeals(
    use_case: Annotated[ListAppealsUseCase, Depends(get_list_appeals_use_case)],
    status_: Annotated[AppealStatus | None, Query(alias="status")] = None,
    category: AppealCategory | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[AppealResponse]:
    """Обращения, новые сверху."""
    page = await use_case.execute(
        PageRequest(limit=limit, offset=offset), status=status_, category=category
    )
    return PageResponse(
        items=[AppealResponse.model_validate(a) for a in page.items], total=page.total
    )


@router.post("/appeals", response_model=AppealResponse, status_code=status.HTTP_201_CREATED)
async def create_appeal(
    body: AppealCreateRequest,
    use_case: Annotated[CreateAppealUseCase, Depends(get_create_appeal_use_case)],
) -> AppealResponse:
    """Создать обращение, проанализировать, привязать служащих и пересчитать их риск (ADR-10)."""
    return AppealResponse.model_validate(await use_case.execute(body.text, body.channel))


@router.get("/appeals/{appeal_id}", response_model=AppealResponse)
async def get_appeal(
    appeal_id: UUID,
    use_case: Annotated[GetAppealUseCase, Depends(get_get_appeal_use_case)],
) -> AppealResponse:
    return AppealResponse.model_validate(await use_case.execute(appeal_id))


@router.post("/appeals/{appeal_id}/reanalyze", response_model=AppealResponse)
async def reanalyze_appeal(
    appeal_id: UUID,
    use_case: Annotated[ReanalyzeAppealUseCase, Depends(get_reanalyze_appeal_use_case)],
) -> AppealResponse:
    """Повторный анализ (например, после смены модели или промпта)."""
    return AppealResponse.model_validate(await use_case.execute(appeal_id))


@router.post("/appeals/{appeal_id}/status", response_model=AppealResponse)
async def change_appeal_status(
    appeal_id: UUID,
    body: AppealStatusRequest,
    use_case: Annotated[ChangeAppealStatusUseCase, Depends(get_change_appeal_status_use_case)],
) -> AppealResponse:
    """Рассмотрение: передать по подведомственности (analyzed → routed) или закрыть."""
    return AppealResponse.model_validate(
        await use_case.execute(appeal_id, AppealStatus(body.status))
    )
