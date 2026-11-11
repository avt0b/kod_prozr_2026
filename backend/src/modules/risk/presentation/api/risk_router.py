from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.schemas import PageResponse
from src.modules.risk.application.use_cases.get_official_flags import GetOfficialFlagsUseCase
from src.modules.risk.application.use_cases.get_official_graph import (
    MAX_DEPTH,
    GetOfficialGraphUseCase,
)
from src.modules.risk.application.use_cases.recompute_risk import RecomputeRiskUseCase
from src.modules.risk.presentation.dependencies import (
    get_official_flags_use_case,
    get_official_graph_use_case,
    get_recompute_risk_use_case,
)
from src.modules.risk.presentation.schemas.risk import (
    GraphResponse,
    RecomputeResponse,
    RiskFlagResponse,
)

router = APIRouter(tags=["Risk"])


@router.get("/officials/{person_id}/graph", response_model=GraphResponse)
async def get_official_graph(
    person_id: UUID,
    use_case: Annotated[GetOfficialGraphUseCase, Depends(get_official_graph_use_case)],
    depth: Annotated[int, Query(ge=1, le=MAX_DEPTH)] = 2,
) -> GraphResponse:
    """Граф связей: служащий, родственники, компании, контракты, органы, обращения."""
    return GraphResponse.model_validate(await use_case.execute(person_id, depth))


@router.get("/officials/{person_id}/flags", response_model=PageResponse[RiskFlagResponse])
async def get_official_flags(
    person_id: UUID,
    use_case: Annotated[GetOfficialFlagsUseCase, Depends(get_official_flags_use_case)],
) -> PageResponse[RiskFlagResponse]:
    """Флаги риска служащего с объяснением, цепочкой доказательств и нормой."""
    flags = await use_case.execute(person_id)
    return PageResponse(items=[RiskFlagResponse.model_validate(f) for f in flags], total=len(flags))


@router.post("/risk/recompute", response_model=RecomputeResponse)
async def recompute_risk(
    use_case: Annotated[RecomputeRiskUseCase, Depends(get_recompute_risk_use_case)],
) -> RecomputeResponse:
    """Пересчитать флаги и баллы по всем служащим."""
    return RecomputeResponse.model_validate(await use_case.execute())
