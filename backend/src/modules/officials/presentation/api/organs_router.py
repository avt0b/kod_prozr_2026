from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.dto import PageRequest
from src.core.dto.page import MAX_PAGE_LIMIT
from src.core.schemas import PageResponse
from src.modules.officials.application.use_cases.list_organs import ListOrgansUseCase
from src.modules.officials.presentation.dependencies import get_list_organs_use_case
from src.modules.officials.presentation.schemas.officials import OrganResponse

router = APIRouter(tags=["Officials"])


@router.get("/organs", response_model=PageResponse[OrganResponse])
async def list_organs(
    use_case: Annotated[ListOrgansUseCase, Depends(get_list_organs_use_case)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = MAX_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[OrganResponse]:
    page = await use_case.execute(PageRequest(limit=limit, offset=offset))
    return PageResponse(
        items=[OrganResponse.model_validate(o) for o in page.items], total=page.total
    )
