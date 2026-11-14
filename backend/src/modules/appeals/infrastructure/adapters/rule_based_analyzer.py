"""Анализатор обращений на словарях и регулярных выражениях — работает без LLM (ADR-05).

Используется, когда LLM_BASE_URL пуст, и как фоллбэк при сбое LLM. Сигналы — из закрытого
списка ai.md §2, конкретность и маршрут считает общий код домена, как и для LLM.
Качество скромное, но детерминированное: на демо не упадёт.
"""

import re
from dataclasses import dataclass

from src.modules.appeals.domain.analysis import (
    ENGINE_FALLBACK,
    AppealAnalysis,
    ExtractedEntity,
    normalize_signals,
    route_of,
    specificity_of,
)
from src.modules.appeals.domain.enums import AppealCategory, EntityType

_FLAGS = re.IGNORECASE | re.UNICODE
MAX_CONFIDENCE = 0.8  # фоллбэк не бывает так же уверен, как LLM
NOT_CORRUPTION_CONFIDENCE = 0.6

# Ключевые слова категорий (основы слов, без учёта регистра).
CATEGORY_KEYWORDS: dict[AppealCategory, tuple[str, ...]] = {
    AppealCategory.BRIBE: (
        r"взят(?:к|оч)",
        r"отк[ао]т",
        r"вымога",
        r"мзд",
        r"в конверте",
        r"незаконн\w* вознагражд",
        r"«?благодарност",
        r"переда\w* (?:ему |ей )?деньг",
        r"требу\w* (?:деньг|оплат)",
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
        r"\bсестр",
        r"\bзят[ья]",
        r"\bтёщ|\bтещ",
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
        r"без (?:всякого )?конкурса",
    ),
    AppealCategory.ABUSE_OF_POWER: (
        r"превыш\w* (?:должностных )?полномоч",
        r"злоупотребл",
        r"служебн\w* положени",
        r"незаконн\w* (?:выдал|отказ|решени)",
        r"давит|давлени",
        r"угрожа",
        r"покрывает",
    ),
}
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

_MONTHS = r"(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-я]*"
_PATRONYMIC = r"[А-ЯЁ][а-яё]+(?:вич|вн|ичн|чн)[а-яё]*"
ENTITY_PATTERNS: tuple[tuple[EntityType, re.Pattern[str]], ...] = (
    # «Иванов Иван Иванович» в любом падеже
    (
        EntityType.PERSON,
        re.compile(rf"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)? [А-ЯЁ][а-яё]+ {_PATRONYMIC}"),
    ),
    # «Андрея Викторовича Соколова»
    (EntityType.PERSON, re.compile(rf"[А-ЯЁ][а-яё]+ {_PATRONYMIC} [А-ЯЁ][а-яё]{{2,}}")),
    # «Иванов И.И.» / «Иванову И. И.»
    (EntityType.PERSON, re.compile(r"[А-ЯЁ][а-яё]{2,}(?:-[А-ЯЁ][а-яё]+)? [А-ЯЁ]\.\s?[А-ЯЁ]\.")),
    # «И.И. Иванов»
    (EntityType.PERSON, re.compile(r"[А-ЯЁ]\.\s?[А-ЯЁ]\.\s?[А-ЯЁ][а-яё]{2,}")),
    (
        EntityType.ORGANIZATION,
        re.compile(
            r"(?:(?:ООО|АО|ПАО|ЗАО|ОАО|ИП|МУП|ГУП|МКУ|МБУ)\s*)?[«\"][А-ЯЁA-Z][^»\"]{1,80}[»\"]"
        ),
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
            rf"\b\d{{1,2}}\.\d{{1,2}}\.\d{{2,4}}\b|\b\d{{1,2}} {_MONTHS}(?: \d{{4}}(?: года?)?)?"
            rf"|\b(?:в|с|до|по) {_MONTHS} \d{{4}}(?: года?)?|\b(?:в|с) \d{{4}} год[уа]",
            _FLAGS,
        ),
    ),
    (
        EntityType.POSITION,
        re.compile(
            r"\b(?:глав[аыуе]|заместител[ьяюем]+|начальник\w*|руководител[ьяюем]+|директор\w*|"
            r"инспектор\w*|специалист\w*|председател[ьяюем]+)(?:\s+(?-i:[а-яё]+)){0,3}",
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
SIGNAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "procurement_ref": re.compile(
        r"(?:закупк\w*|контракт\w*|извещени\w*|договор\w*)\s*(?:№|N|номер)\s*\d{3,}|№\s*\d{6,}",
        _FLAGS,
    ),
    "relative_mentioned": re.compile(
        r"родственн|\bжен[аеуы]\b|\bсупруг|\bмуж[аеу]?\b|\bсын[аеу]?\b|\bдоч[ьери]|\bбрат[аеу]?\b"
        r"|\bсестр|\bзят[ья]|\bтёщ|\bтещ|\bсвекр|\bшурин",
        _FLAGS,
    ),
    "extortion": re.compile(r"вымога|угрож|требу\w* (?:деньг|оплат)|давит|давлени", _FLAGS),
    "evidence_available": re.compile(
        r"аудиозапис|видеозапис|запис\w* разговор|свидетел|переписк|документ\w* (?:есть|прилага)"
        r"|прилага\w*|скриншот|фото",
        _FLAGS,
    ),
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
        keyword_total = sum(h.count for h in corrupt_hits)
        confidence = (
            round(min(MAX_CONFIDENCE, 0.5 + 0.1 * keyword_total), 2)
            if is_corruption
            else NOT_CORRUPTION_CONFIDENCE
        )
        codes = {code for code, pattern in SIGNAL_PATTERNS.items() if pattern.search(text)}
        signals = normalize_signals(codes, entities, is_corruption)
        signal_codes = frozenset(s.code for s in signals)
        specificity = specificity_of(signal_codes)
        return AppealAnalysis(
            is_corruption=is_corruption,
            category=category,
            confidence=confidence,
            specificity=specificity,
            route_to=route_of(is_corruption, category, signal_codes, specificity),
            summary=_summary(text, category),
            entities=entities,
            signals=signals,
            analyzer=self.name,
            engine=ENGINE_FALLBACK,
        )


def extract_entities(text: str) -> tuple[ExtractedEntity, ...]:
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
    return tuple(sorted(entities, key=lambda e: e.start))


_GREETING = re.compile(
    r"^(?:здравствуйте|добрый день|добрый вечер|доброе утро|уважаемые?\b|прошу|помогите"
    r"|сколько можно|это просто|я больше не могу|довожу)",
    _FLAGS,
)


def _summary(text: str, category: AppealCategory) -> str:
    """Первое содержательное предложение: приветствия и эмоции не отличают обращения друг от
    друга, а R07 считает обращения с одинаковым кратким содержанием дублями."""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    meaningful = [s for s in sentences if not _GREETING.match(s) and len(s.split()) >= 4]
    first = (meaningful or sentences or [text.strip()])[0]
    if len(first) > 200:
        first = first[:197].rstrip() + "..."
    return f"{CATEGORY_LABELS[category]}: {first}"
