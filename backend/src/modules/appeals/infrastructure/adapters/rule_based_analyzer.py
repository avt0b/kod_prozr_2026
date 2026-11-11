"""Анализатор обращений на словарях и регулярных выражениях — работает без LLM.

Используется как фейк в dev/тестах (LLM_BASE_URL пуст) и как фоллбэк при сбое LLM (ADR-05).
Качество скромное, но детерминированное: на демо не упадёт.
"""

import re
from dataclasses import dataclass

from src.modules.appeals.domain.analysis import (
    CORRUPTION_ROUTE,
    GENERAL_ROUTE,
    AppealAnalysis,
    ExtractedEntity,
    Signal,
)
from src.modules.appeals.domain.enums import AppealCategory, EntityType

_FLAGS = re.IGNORECASE | re.UNICODE

# Ключевые слова категорий (основы слов, без учёта регистра).
CATEGORY_KEYWORDS: dict[AppealCategory, tuple[str, ...]] = {
    AppealCategory.BRIBE: (
        r"взятк",
        r"отк[ао]т",
        r"вымога",
        r"мзд",
        r"в конверте",
        r"незаконн\w* вознагражд",
        r"переда\w* (?:ему |ей )?деньг",
        r"требовал\w* (?:деньг|оплат)",
    ),
    AppealCategory.CONFLICT_OF_INTEREST: (
        r"конфликт\w* интерес",
        r"родственник",
        r"\bжен[аеуы]\b",
        r"\bсупруг",
        r"\bмуж[аеу]?\b",
        r"\bсын[аеу]?\b",
        r"\bдоч[ьери]",
        r"\bбрат[аеу]?\b",
        r"\bзят[ья]",
        r"аффилир",
        r"фирм\w* (?:его|её|ее|своей|своего)",
    ),
    AppealCategory.PROCUREMENT: (
        r"закупк",
        r"тендер",
        r"аукцион",
        r"госконтракт",
        r"контракт",
        r"единственн\w* поставщик",
        r"поставщик",
        r"подрядчик",
        r"завышен\w* цен",
    ),
    AppealCategory.ABUSE_OF_POWER: (
        r"превышени\w* (?:должностных )?полномоч",
        r"злоупотребл",
        r"служебн\w* положени",
        r"незаконн\w* (?:выдал|отказ|решени)",
        r"давлени",
        r"угрожа",
        r"покрывает",
    ),
}
# Порядок при равенстве числа совпадений.
CATEGORY_PRIORITY = (
    AppealCategory.BRIBE,
    AppealCategory.CONFLICT_OF_INTEREST,
    AppealCategory.PROCUREMENT,
    AppealCategory.ABUSE_OF_POWER,
)
CATEGORY_LABELS = {
    AppealCategory.BRIBE: "Возможная взятка",
    AppealCategory.CONFLICT_OF_INTEREST: "Возможный конфликт интересов",
    AppealCategory.PROCUREMENT: "Возможные нарушения в закупках",
    AppealCategory.ABUSE_OF_POWER: "Возможное злоупотребление полномочиями",
    AppealCategory.OTHER: "Обращение без признаков коррупции",
}

_PATRONYMIC = r"[А-ЯЁ][а-яё]+(?:вич|вн|ичн|чн)[а-яё]*"
ENTITY_PATTERNS: tuple[tuple[EntityType, re.Pattern[str]], ...] = (
    # «Иванов Иван Иванович» в любом падеже
    (
        EntityType.PERSON,
        re.compile(rf"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)? [А-ЯЁ][а-яё]+ {_PATRONYMIC}"),
    ),
    # «Иванов И.И.» / «Иванову И. И.»
    (EntityType.PERSON, re.compile(r"[А-ЯЁ][а-яё]{2,}(?:-[А-ЯЁ][а-яё]+)? [А-ЯЁ]\.\s?[А-ЯЁ]\.")),
    # «И.И. Иванов»
    (EntityType.PERSON, re.compile(r"[А-ЯЁ]\.\s?[А-ЯЁ]\.\s?[А-ЯЁ][а-яё]{2,}")),
    (
        EntityType.ORGANIZATION,
        re.compile(r"(?:ООО|АО|ПАО|ЗАО|ОАО|ИП|МУП|ГУП|МКУ|МБУ)\s*[«\"][^»\"]{2,80}[»\"]"),
    ),
    (
        EntityType.MONEY,
        re.compile(
            r"\d[\d\s]*(?:[.,]\d+)?\s*(?:тыс\.?|тысяч\w*|млн\.?|миллион\w*|млрд\.?)?\s*"
            r"(?:руб(?:лей|ля|ль|\.)?|₽)",
            _FLAGS,
        ),
    ),
    (
        EntityType.DATE,
        re.compile(
            r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b|\b\d{1,2} (?:января|февраля|марта|апреля|мая|июня|"
            r"июля|августа|сентября|октября|ноября|декабря)(?: \d{4})?",
            _FLAGS,
        ),
    ),
    (
        EntityType.POSITION,
        re.compile(
            r"\b(?:глав[аыуе]|заместител[ьяю]|начальник\w*|руководител[ьяю]|директор\w*|"
            r"инспектор\w*|специалист\w*|председател[ьяю])(?:\s+[а-яё]+){0,3}",
            _FLAGS,
        ),
    ),
    (
        EntityType.ADDRESS,
        re.compile(
            r"(?:ул\.|улиц[аеы]|пр-т|проспект\w*|пер\.|переул\w*)\s*[А-ЯЁ][а-яё]+"
            r"(?:,?\s*(?:д\.|дом)\s*\d+[а-я]?)?",
            _FLAGS,
        ),
    ),
)

SPECIFICITY_WEIGHTS = {
    EntityType.PERSON: 0.3,
    EntityType.MONEY: 0.2,
    EntityType.DATE: 0.15,
    EntityType.ORGANIZATION: 0.15,
    EntityType.POSITION: 0.1,
    EntityType.ADDRESS: 0.1,
}
SIGNALS = {
    EntityType.PERSON: ("named_official", "назван конкретный служащий"),
    EntityType.MONEY: ("money_amount", "указана сумма"),
    EntityType.DATE: ("date_specified", "указаны дата или период"),
    EntityType.ORGANIZATION: ("organization_named", "названа организация"),
    EntityType.POSITION: ("position_named", "названа должность"),
}
CATEGORY_SIGNALS = {
    AppealCategory.BRIBE: ("bribe_keywords", "упоминание денежного вознаграждения"),
    AppealCategory.CONFLICT_OF_INTEREST: (
        "kinship_or_affiliation",
        "упомянуты родство/аффилированность",
    ),
    AppealCategory.PROCUREMENT: ("procurement_keywords", "речь о закупках и контрактах"),
    AppealCategory.ABUSE_OF_POWER: ("abuse_keywords", "признаки злоупотребления полномочиями"),
}


@dataclass(frozen=True)
class _Hit:
    category: AppealCategory
    count: int


class RuleBasedAppealAnalyzer:
    """Реализует порт AppealAnalyzer. Без состояния и без сети."""

    name = "rules"

    async def analyze(self, text: str) -> AppealAnalysis:
        return self.analyze_sync(text)

    def analyze_sync(self, text: str) -> AppealAnalysis:
        hits = [
            _Hit(category, sum(len(re.findall(p, text, _FLAGS)) for p in patterns))
            for category, patterns in CATEGORY_KEYWORDS.items()
        ]
        hits = [h for h in hits if h.count > 0]
        entities = extract_entities(text)
        entity_types = {e.type for e in entities}

        # Родство само по себе — не коррупция; нужен ещё «денежный»/«закупочный» контекст.
        corrupt_hits = [
            h
            for h in hits
            if h.category is not AppealCategory.CONFLICT_OF_INTEREST
            or any(o.category is not AppealCategory.CONFLICT_OF_INTEREST for o in hits)
            or EntityType.ORGANIZATION in entity_types
        ]
        is_corruption = bool(corrupt_hits)
        category = (
            max(
                corrupt_hits, key=lambda h: (h.count, -CATEGORY_PRIORITY.index(h.category))
            ).category
            if corrupt_hits
            else AppealCategory.OTHER
        )

        specificity = round(min(1.0, sum(SPECIFICITY_WEIGHTS[t] for t in entity_types)), 2)
        keyword_total = sum(h.count for h in corrupt_hits)
        confidence = round(min(0.9, 0.5 + 0.1 * keyword_total), 2) if is_corruption else 0.6

        signals = [Signal(*SIGNALS[t]) for t in SIGNALS if t in entity_types]
        signals += [Signal(*CATEGORY_SIGNALS[h.category]) for h in corrupt_hits]

        return AppealAnalysis(
            is_corruption=is_corruption,
            category=category,
            confidence=confidence,
            specificity=specificity,
            route_to=CORRUPTION_ROUTE if is_corruption else GENERAL_ROUTE,
            summary=_summary(text, category),
            entities=tuple(entities),
            signals=tuple(signals),
            analyzer=self.name,
        )


def extract_entities(text: str) -> list[ExtractedEntity]:
    """Сущности без пересечений: при наложении выигрывает найденная раньше по списку шаблонов."""
    taken: list[tuple[int, int]] = []
    entities: list[ExtractedEntity] = []
    for entity_type, pattern in ENTITY_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            value = match.group(0).rstrip(" ,.;")
            end = start + len(value)
            if any(start < t_end and t_start < end for t_start, t_end in taken):
                continue
            taken.append((start, end))
            entities.append(ExtractedEntity(entity_type, value, start, end))
    return sorted(entities, key=lambda e: e.start)


def _summary(text: str, category: AppealCategory) -> str:
    first = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
    if len(first) > 200:
        first = first[:197].rstrip() + "..."
    return f"{CATEGORY_LABELS[category]}: {first}"
