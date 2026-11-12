"""DTO контекста appeals. Наружу из use case уходят они, а не агрегат Appeal."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.appeals.domain.analysis import AppealAnalysis
from src.modules.appeals.domain.appeal import Appeal


@dataclass(frozen=True)
class PersonRef:
    """Человек из реестра officials глазами appeals: только id и ФИО."""

    id: UUID
    full_name: str
    position: str | None = None
    organ: str | None = None
    risk_score: float = 0.0


@dataclass(frozen=True)
class EntityDTO:
    type: str
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class SignalDTO:
    code: str
    text: str


@dataclass(frozen=True)
class AnalysisDTO:
    is_corruption: bool
    category: str
    confidence: float
    entities: tuple[EntityDTO, ...]
    signals: tuple[SignalDTO, ...]
    specificity: float
    route_to: str
    summary: str
    analyzer: str

    @classmethod
    def from_value(cls, analysis: AppealAnalysis) -> "AnalysisDTO":
        return cls(
            is_corruption=analysis.is_corruption,
            category=analysis.category.value,
            confidence=analysis.confidence,
            entities=tuple(
                EntityDTO(e.type.value, e.text, e.start, e.end) for e in analysis.entities
            ),
            signals=tuple(SignalDTO(s.code, s.text) for s in analysis.signals),
            specificity=analysis.specificity,
            route_to=analysis.route_to,
            summary=analysis.summary,
            analyzer=analysis.analyzer,
        )


@dataclass(frozen=True)
class AppealDTO:
    id: UUID
    received_at: datetime
    channel: str
    text: str
    status: str
    analysis: AnalysisDTO | None
    linked_person_ids: tuple[UUID, ...]
    linked_persons: tuple[PersonRef, ...] = ()

    @classmethod
    def from_entity(
        cls, appeal: Appeal, persons: dict[UUID, PersonRef] | None = None
    ) -> "AppealDTO":
        persons = persons or {}
        return cls(
            id=appeal.id,
            received_at=appeal.received_at,
            channel=appeal.channel,
            text=appeal.text,
            status=appeal.status.value,
            analysis=AnalysisDTO.from_value(appeal.analysis) if appeal.analysis else None,
            linked_person_ids=appeal.linked_person_ids,
            linked_persons=tuple(persons[p] for p in appeal.linked_person_ids if p in persons),
        )


@dataclass(frozen=True)
class AppealMentionDTO:
    """Упоминание человека в обращении — published language для risk (R07, граф)."""

    appeal_id: UUID
    person_id: UUID
    is_corruption: bool
    category: str | None
    confidence: float
    specificity: float
    received_at: datetime
    summary: str | None
