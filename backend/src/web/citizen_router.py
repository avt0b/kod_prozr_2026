"""Кабинет гражданина (#70): подать обращение и следить за статусом своих обращений.

Гражданин не видит анализ, кандидатов и привязанных служащих — это рабочие данные аналитика.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.auth import require_citizen
from src.core.infrastructure.database.models.auth import CitizenAppealModel, UserModel
from src.core.infrastructure.dependencies import get_session
from src.core.schemas import APIModel, PageResponse, SafeString
from src.modules.appeals.application.use_cases.create_appeal import CreateAppealUseCase
from src.modules.appeals.infrastructure.database.models.appeal import AppealModel
from src.modules.appeals.presentation.dependencies import get_create_appeal_use_case

router = APIRouter(prefix="/citizen", tags=["Citizen"])
Citizen = Annotated[UserModel, Depends(require_citizen)]
DB = Annotated[AsyncSession, Depends(get_session)]


class CitizenAppealCreate(APIModel):
    text: SafeString = Field(min_length=20, max_length=20_000)


class CitizenAppealResponse(APIModel):
    id: UUID
    received_at: datetime
    text: str
    status: str


@router.post("/appeals", response_model=CitizenAppealResponse, status_code=status.HTTP_201_CREATED)
async def submit_appeal(
    body: CitizenAppealCreate,
    user: Citizen,
    db: DB,
    use_case: Annotated[CreateAppealUseCase, Depends(get_create_appeal_use_case)],
) -> CitizenAppealResponse:
    """Подать обращение: тот же анализ и пересчёт риска, что и при вводе аналитиком (ADR-10)."""
    appeal = await use_case.execute(body.text, "web")
    db.add(CitizenAppealModel(appeal_id=appeal.id, user_id=user.id))
    await db.commit()
    return CitizenAppealResponse(
        id=appeal.id, received_at=appeal.received_at, text=appeal.text, status=appeal.status
    )


@router.get("/appeals", response_model=PageResponse[CitizenAppealResponse])
async def my_appeals(
    user: Citizen,
    db: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[CitizenAppealResponse]:
    """Свои обращения, новые сверху."""
    mine = (
        select(AppealModel)
        .join(CitizenAppealModel, CitizenAppealModel.appeal_id == AppealModel.id)
        .where(CitizenAppealModel.user_id == user.id)
    )
    total = (await db.execute(select(func.count()).select_from(mine.subquery()))).scalar_one()
    rows = (
        await db.execute(mine.order_by(AppealModel.received_at.desc()).limit(limit).offset(offset))
    ).scalars()
    return PageResponse(
        items=[
            CitizenAppealResponse(id=r.id, received_at=r.received_at, text=r.text, status=r.status)
            for r in rows
        ],
        total=total,
    )
