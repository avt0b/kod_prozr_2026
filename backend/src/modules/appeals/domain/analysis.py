from dataclasses import dataclass, field
from uuid import UUID

from src.modules.appeals.domain.enums import AppealCategory, EntityType
from src.modules.appeals.domain.exceptions import InvalidAnalysisError

# Маршрутизация (ai.md §2). Решение о передаче в правоохранительные органы принимает аналитик.
GENERAL_ROUTE = "Рассмотрение по компетенции в общем порядке"
CORRUPTION_ROUTE = "Подразделение по профилактике коррупционных правонарушений"
LAW_ENFORCEMENT_NOTE = "рекомендуется рассмотреть направление в правоохранительные органы"
LAW_ENFORCEMENT_SPECIFICITY = 0.6

ENGINE_LLM = "llm"
ENGINE_FALLBACK = "fallback"

# Закрытый список риск-сигналов (ai.md §2): код -> текст для человека.
SIGNALS: dict[str, str] = {
    "named_official": "назван конкретный служащий",
    "named_position": "названа должность или подразделение",
    "named_organization": "названа компания",
    "money_amount": "указана сумма",
    "specific_date": "указана дата или период",
    "procurement_ref": "указан номер закупки, контракта или объект",
    "relative_mentioned": "упомянут родственник",
    "extortion": "вымогательство или давление",
    "evidence_available": "есть документы, записи или свидетели",
    "repeated_subject": "служащий уже упоминался в других обращениях",
    "vague_no_facts": "нет проверяемых фактов",
}
FACT_SIGNALS = frozenset(SIGNALS) - {"named_official", "named_position", "vague_no_facts"}
# Сущность в тексте сама по себе подтверждает сигнал.
ENTITY_SIGNALS: dict[EntityType, str] = {
    EntityType.PERSON: "named_official",
    EntityType.POSITION: "named_position",
    EntityType.ORGANIZATION: "named_organization",
    EntityType.MONEY: "money_amount",
    EntityType.DATE: "specific_date",
}


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

    @classmethod
    def of(cls, code: str) -> "Signal":
        return cls(code, SIGNALS.get(code, code))


@dataclass(frozen=True)
class MatchCandidate:
    """Служащий, похожий на упомянутого, но не привязанный автоматически (ai.md §3)."""

    person_id: UUID
    full_name: str
    score: float


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
    engine: str = ENGINE_FALLBACK  # контракт: llm | fallback
    candidates: tuple[MatchCandidate, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise InvalidAnalysisError("confidence must be within 0..1")
        if not 0 <= self.specificity <= 1:
            raise InvalidAnalysisError("specificity must be within 0..1")

    def person_mentions(self) -> list[str]:
        return [e.text for e in self.entities if e.type is EntityType.PERSON]

    def mentions_of(self, *types: EntityType) -> list[str]:
        return [e.text for e in self.entities if e.type in types]

    @property
    def signal_codes(self) -> frozenset[str]:
        return frozenset(s.code for s in self.signals)


def normalize_signals(
    codes: set[str] | frozenset[str], entities: tuple[ExtractedEntity, ...], is_corruption: bool
) -> tuple[Signal, ...]:
    """Только коды из закрытого списка; сигналы, подтверждённые сущностями, добавляются;
    vague_no_facts — только у коррупционного обращения без проверяемых фактов."""
    result = {code for code in codes if code in SIGNALS}
    result |= {ENTITY_SIGNALS[e.type] for e in entities if e.type in ENTITY_SIGNALS}
    if result & FACT_SIGNALS or not is_corruption:
        result.discard("vague_no_facts")
    else:
        result.add("vague_no_facts")
    return tuple(Signal.of(code) for code in SIGNALS if code in result)


def specificity_of(codes: frozenset[str] | set[str]) -> float:
    """Конкретность обращения по сигналам (ai.md §2). Считает код, а не LLM."""
    value = (
        0.30 * bool(codes & {"named_official", "named_position"})
        + 0.20 * ("named_organization" in codes)
        + 0.20 * ("money_amount" in codes)
        + 0.15 * ("specific_date" in codes)
        + 0.15 * bool(codes & {"procurement_ref", "evidence_available"})
    )
    if "vague_no_facts" in codes:
        value *= 0.5
    return round(min(1.0, value), 2)


def route_of(
    is_corruption: bool,
    category: AppealCategory,
    codes: frozenset[str] | set[str],
    specificity: float,
) -> str:
    """Маршрут по таблице ai.md §2."""
    if not is_corruption:
        return GENERAL_ROUTE
    serious = category is AppealCategory.BRIBE or "extortion" in codes
    if serious and specificity >= LAW_ENFORCEMENT_SPECIFICITY:
        return f"{CORRUPTION_ROUTE}; {LAW_ENFORCEMENT_NOTE}"
    return CORRUPTION_ROUTE


def entity_spans(text: str, items: list[tuple[EntityType, str]]) -> tuple[ExtractedEntity, ...]:
    """Смещения сущностей ищет код: LLM в позициях ошибается (ai.md §2).

    Сущность, которой нет в тексте дословно, выбрасывается как галлюцинация. Повторяющийся
    текст получает следующее вхождение; пересекающиеся сущности не дублируются.
    """
    taken: list[tuple[int, int]] = []
    result: list[ExtractedEntity] = []
    for entity_type, raw in items:
        value = raw.strip().strip(".,;:!?")
        if len(value) < 2:
            continue
        start = text.find(value)
        while start >= 0 and any(start < e and s < start + len(value) for s, e in taken):
            start = text.find(value, start + 1)
        if start < 0:
            continue
        end = start + len(value)
        taken.append((start, end))
        result.append(ExtractedEntity(entity_type, value, start, end))
    return tuple(sorted(result, key=lambda e: e.start))
