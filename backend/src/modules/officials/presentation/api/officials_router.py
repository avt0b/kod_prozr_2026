from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.core.dto import PageRequest
from src.core.dto.page import MAX_PAGE_LIMIT
from src.core.schemas import PageResponse
from src.modules.officials.application.use_cases.get_official_profile import (
    GetOfficialProfileUseCase,
)
from src.modules.officials.application.use_cases.list_officials import (
    ListOfficialsUseCase,
    OfficialsFilter,
    OfficialsSort,
)
from src.modules.officials.presentation.dependencies import (
    get_list_officials_use_case,
    get_official_profile_use_case,
)
from src.modules.officials.presentation.schemas.officials import (
    AppointmentResponse,
    AuthorityResponse,
    CompanyLinkResponse,
    EmploymentResponse,
    OfficialListItemResponse,
    OfficialProfileResponse,
    OfficialRiskResponse,
    OrganResponse,
    PersonResponse,
    PositionResponse,
    RelativeResponse,
)

router = APIRouter(tags=["Officials"])


@router.get("/officials", response_model=PageResponse[OfficialListItemResponse])
async def list_officials(
    use_case: Annotated[ListOfficialsUseCase, Depends(get_list_officials_use_case)],
    query: Annotated[str | None, Query(max_length=200)] = None,
    organ_id: UUID | None = None,
    min_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    sort: OfficialsSort = OfficialsSort.RISK_DESC,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[OfficialListItemResponse]:
    """Рейтинг служащих по риск-баллу с фильтрами."""
    page = await use_case.execute(
        OfficialsFilter(query=query, organ_id=organ_id, min_score=min_score, sort=sort),
        PageRequest(limit=limit, offset=offset),
    )
    return PageResponse(
        items=[OfficialListItemResponse.model_validate(i) for i in page.items], total=page.total
    )


@router.get("/officials/{person_id}", response_model=OfficialProfileResponse)
async def get_official(
    person_id: UUID,
    use_case: Annotated[GetOfficialProfileUseCase, Depends(get_official_profile_use_case)],
) -> OfficialProfileResponse:
    """Профиль служащего: должности, полномочия, родственники, компании, риск."""
    profile = await use_case.execute(person_id)
    return OfficialProfileResponse(
        person=PersonResponse.model_validate(profile.person),
        appointments=[
            AppointmentResponse(
                id=a.id,
                started_at=a.started_at,
                ended_at=a.ended_at,
                is_active=a.is_active,
                position=PositionResponse.model_validate(a.position),
                organ=OrganResponse.model_validate(a.organ),
                authorities=[AuthorityResponse.from_dto(x) for x in a.authorities],
            )
            for a in profile.appointments
        ],
        authorities=[AuthorityResponse.from_dto(x) for x in profile.authorities],
        relatives=[RelativeResponse.model_validate(r) for r in profile.relatives],
        companies=[CompanyLinkResponse.model_validate(c) for c in profile.companies],
        employments=[EmploymentResponse.model_validate(e) for e in profile.employments],
        risk=OfficialRiskResponse.model_validate(profile.risk),
    )
