from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.modules.appeals.domain.appeal import Appeal
from src.modules.appeals.domain.enums import AppealStatus
from src.modules.appeals.infrastructure.serialization import AnalysisSchema


class AppealSeed(BaseModel):
    """Строка appeals.json. analysis = null -> анализ посчитается при сидировании."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    received_at: datetime
    channel: str
    text: str
    status: AppealStatus = AppealStatus.NEW
    analysis: dict[str, Any] | None = None
    linked_person_ids: list[UUID] = []

    def to_entity(self) -> Appeal:
        analysis = (
            AnalysisSchema.model_validate(self.analysis).to_domain(self.text)
            if self.analysis
            else None
        )
        status = self.status if analysis is not None else AppealStatus.NEW
        return Appeal(
            id=self.id,
            text=self.text,
            channel=self.channel,
            received_at=self.received_at,
            status=status,
            analysis=analysis,
            linked_person_ids=tuple(self.linked_person_ids),
        )
