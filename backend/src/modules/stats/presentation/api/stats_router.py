from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.dto import PageRequest
from src.core.dto.page import MAX_PAGE_LIMIT
from src.modules.stats.application.use_cases.get_overview import GetOverviewUseCase
from src.modules.stats.application.use_cases.get_risk_map import GetRiskMapUseCase
from src.modules.stats.presentation.dependencies import (
    get_overview_use_case,
    get_risk_map_use_case,
)
from src.modules.stats.presentation.schemas.risk_map import RiskMapResponse
from src.modules.stats.presentation.schemas.stats import OverviewResponse

router = APIRouter(tags=["Stats"])


@router.get("/stats/overview", response_model=OverviewResponse)
async def get_overview(
    use_case: Annotated[GetOverviewUseCase, Depends(get_overview_use_case)],
) -> OverviewResponse:
    """Счётчики для главной: служащие, флаги по уровням, обращения по статусам."""
    return OverviewResponse.model_validate(await use_case.execute())


@router.get("/risk-map", response_model=RiskMapResponse)
async def get_risk_map(
    use_case: Annotated[GetRiskMapUseCase, Depends(get_risk_map_use_case)],
    organ_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = MAX_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RiskMapResponse:
    """Карта рисков: должности и органы с долей служащих с флагами, баллами и типовыми рисками."""
    result = await use_case.execute(organ_id, PageRequest(limit=limit, offset=offset))
    return RiskMapResponse.from_dto(result)
