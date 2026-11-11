"""JSON-форма анализа обращения (контракт: Appeal.analysis).

Одна схема на три места: JSONB в БД, ответ LLM, файл сида. Pydantic живёт здесь,
в infrastructure, — в домене он запрещён.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.modules.appeals.domain.analysis import (
    CORRUPTION_ROUTE,
    GENERAL_ROUTE,
    AppealAnalysis,
    ExtractedEntity,
    Signal,
)
from src.modules.appeals.domain.enums import AppealCategory, EntityType


class EntitySchema(BaseModel):
    type: EntityType
    text: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class SignalSchema(BaseModel):
    code: str
    text: str


class AnalysisSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    is_corruption: bool
    category: AppealCategory = AppealCategory.OTHER
    confidence: float = Field(ge=0, le=1)
    entities: list[EntitySchema] = Field(default_factory=list)
    signals: list[SignalSchema] = Field(default_factory=list)
    specificity: float = Field(default=0.0, ge=0, le=1)
    route_to: str | None = None
    summary: str = ""
    analyzer: str = "unknown"

    @field_validator("category", mode="before")
    @classmethod
    def unknown_category_is_other(cls, value: Any) -> Any:
        allowed = {c.value for c in AppealCategory}
        return value if value in allowed else AppealCategory.OTHER.value

    def to_domain(self, text: str | None = None) -> AppealAnalysis:
        """text — исходник обращения: смещения сущностей сверяются и чинятся по нему."""
        entities: list[ExtractedEntity] = []
        for entity in self.entities:
            start, end = entity.start, entity.end
            if text is not None and text[start:end] != entity.text:
                found = text.find(entity.text)
                if found < 0:
                    continue  # модель выдумала сущность, которой нет в тексте
                start, end = found, found + len(entity.text)
            entities.append(ExtractedEntity(entity.type, entity.text, start, end))
        route = self.route_to or (CORRUPTION_ROUTE if self.is_corruption else GENERAL_ROUTE)
        return AppealAnalysis(
            is_corruption=self.is_corruption,
            category=self.category,
            confidence=self.confidence,
            specificity=self.specificity,
            route_to=route,
            summary=self.summary,
            entities=tuple(entities),
            signals=tuple(Signal(s.code, s.text) for s in self.signals),
            analyzer=self.analyzer,
        )

    @classmethod
    def from_domain(cls, analysis: AppealAnalysis) -> "AnalysisSchema":
        return cls(
            is_corruption=analysis.is_corruption,
            category=analysis.category,
            confidence=analysis.confidence,
            entities=[
                EntitySchema(type=e.type, text=e.text, start=e.start, end=e.end)
                for e in analysis.entities
            ],
            signals=[SignalSchema(code=s.code, text=s.text) for s in analysis.signals],
            specificity=analysis.specificity,
            route_to=analysis.route_to,
            summary=analysis.summary,
            analyzer=analysis.analyzer,
        )


def analysis_to_json(analysis: AppealAnalysis | None) -> dict[str, Any] | None:
    return (
        None if analysis is None else AnalysisSchema.from_domain(analysis).model_dump(mode="json")
    )


def analysis_from_json(data: dict[str, Any] | None) -> AppealAnalysis | None:
    return None if data is None else AnalysisSchema.model_validate(data).to_domain()
