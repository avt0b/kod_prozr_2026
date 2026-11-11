from datetime import datetime
from uuid import UUID

from src.core.schemas import APIModel


class ReportCreateRequest(APIModel):
    person_id: UUID


class ReportDraftResponse(APIModel):
    id: UUID
    person_id: UUID
    text: str
    generator: str
    created_at: datetime
