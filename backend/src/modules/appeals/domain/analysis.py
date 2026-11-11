from dataclasses import dataclass, field

from src.modules.appeals.domain.enums import AppealCategory, EntityType
from src.modules.appeals.domain.exceptions import InvalidAnalysisError

CORRUPTION_ROUTE = "отдел по профилактике коррупционных правонарушений"
GENERAL_ROUTE = "отдел по работе с обращениями граждан"


@dataclass(frozen=True)
class ExtractedEntity:
    """Сущность из текста. start/end — смещения в символах (end не включительно)."""

    type: EntityType
    text: str
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise InvalidAnalysisError(f"bad entity span {self.start}..{self.end}")


@dataclass(frozen=True)
class Signal:
    """Риск-сигнал в обращении: код для машины, текст для человека."""

    code: str
    text: str


@dataclass(frozen=True)
class AppealAnalysis:
    """Результат анализа обращения (контракт: Appeal.analysis)."""

    is_corruption: bool
    category: AppealCategory
    confidence: float
    specificity: float
    route_to: str
    summary: str
    entities: tuple[ExtractedEntity, ...] = field(default_factory=tuple)
    signals: tuple[Signal, ...] = field(default_factory=tuple)
    analyzer: str = "unknown"  # кто анализировал: rules / llm:<model> — для отладки и демо

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise InvalidAnalysisError("confidence must be within 0..1")
        if not 0 <= self.specificity <= 1:
            raise InvalidAnalysisError("specificity must be within 0..1")

    def person_mentions(self) -> list[str]:
        return [e.text for e in self.entities if e.type is EntityType.PERSON]
