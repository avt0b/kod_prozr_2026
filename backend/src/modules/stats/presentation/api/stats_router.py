from typing import Annotated

from fastapi import APIRouter, Depends

from src.modules.stats.application.use_cases.get_overview import GetOverviewUseCase
from src.modules.stats.presentation.dependencies import get_overview_use_case
from src.modules.stats.presentation.schemas.stats import OverviewResponse

router = APIRouter(tags=["Stats"])


@router.get("/stats/overview", response_model=OverviewResponse)
async def get_overview(
    use_case: Annotated[GetOverviewUseCase, Depends(get_overview_use_case)],
) -> OverviewResponse:
    """Счётчики для главной: служащие, флаги по уровням, обращения по статусам."""
    return OverviewResponse.model_validate(await use_case.execute())
