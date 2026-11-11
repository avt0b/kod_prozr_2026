from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.modules.reports.application.use_cases.create_report_draft import (
    CreateReportDraftUseCase,
)
from src.modules.reports.application.use_cases.get_report_draft import GetReportDraftUseCase
from src.modules.reports.presentation.dependencies import (
    get_create_report_use_case,
    get_get_report_use_case,
)
from src.modules.reports.presentation.schemas.reports import (
    ReportCreateRequest,
    ReportDraftResponse,
)

router = APIRouter(tags=["Reports"])


@router.post("/reports", response_model=ReportDraftResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    body: ReportCreateRequest,
    use_case: Annotated[CreateReportDraftUseCase, Depends(get_create_report_use_case)],
) -> ReportDraftResponse:
    """Черновик докладной записки по служащему (LLM или шаблон)."""
    return ReportDraftResponse.model_validate(await use_case.execute(body.person_id))


@router.get("/reports/{report_id}", response_model=ReportDraftResponse)
async def get_report(
    report_id: UUID,
    use_case: Annotated[GetReportDraftUseCase, Depends(get_get_report_use_case)],
) -> ReportDraftResponse:
    return ReportDraftResponse.model_validate(await use_case.execute(report_id))
