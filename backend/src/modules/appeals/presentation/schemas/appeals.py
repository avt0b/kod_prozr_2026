from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.core.schemas import APIModel, SafeString


class AppealCreateRequest(APIModel):
    text: SafeString = Field(min_length=1, max_length=20_000)
    # Значения из docs/data.md: web | email | letter | hotline (в контракт ещё не внесены).
    channel: SafeString = Field(default="web", min_length=1, max_length=32)


class EntityResponse(APIModel):
    type: str
    text: str
    start: int
    end: int


class SignalResponse(APIModel):
    code: str
    text: str


class AnalysisResponse(APIModel):
    is_corruption: bool
    category: str
    confidence: float
    entities: list[EntityResponse]
    signals: list[SignalResponse]
    specificity: float
    route_to: str
    summary: str
    analyzer: str


class LinkedPersonResponse(APIModel):
    id: UUID
    full_name: str
    position: str | None = None
    organ: str | None = None
    risk_score: float = 0.0


class AppealResponse(APIModel):
    id: UUID
    received_at: datetime
    channel: str
    text: str
    status: str
    analysis: AnalysisResponse | None
    linked_person_ids: list[UUID]
    linked_persons: list[LinkedPersonResponse]
