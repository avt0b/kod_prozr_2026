"""Сопоставление упомянутых в обращении лиц с профилями служащих (AI-05, docs/ai.md §3).

1. Нормализация: нижний регистр, ё→е, каждый токен — в именительный падеж через pymorphy3
   («Соколову Андрею Викторовичу» → «соколов андрей викторович»). Инициалы остаются буквами.
2. Кандидаты: фамилия ~ фамилия служащего (rapidfuzz.ratio ≥ 85: падежи, опечатки).
3. Совместимость имени и отчества (или инициалов): противоречие исключает кандидата.
4. Контекст: должность или орган из текста повышают балл служащего с такой должностью.
5. Балл = 0.5·фамилия + 0.25·имя и отчество + 0.25·должность или орган:
   ≥ 0.8 и кандидат единственный — привязка; 0.5–0.8 или несколько — только кандидаты.
6. Только должность без ФИО: кандидаты — те, кто замещал её на дату обращения, без привязки.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any
from uuid import UUID

from rapidfuzz import fuzz

from src.modules.appeals.application.interfaces.person_matcher import (
    MatchResult,
    OfficialCard,
    OfficialPost,
)
from src.modules.appeals.domain.analysis import AppealAnalysis, MatchCandidate
from src.modules.appeals.domain.enums import EntityType

SURNAME_THRESHOLD = 85  # ratio фамилий: «Саколов» ~ «Соколов» = 85.7
LINK_SCORE = 0.8
CANDIDATE_SCORE = 0.5
POSITION_CANDIDATE_SCORE = 0.6
MAX_POSITION_CANDIDATES = 3
_WORD = re.compile(r"[А-ЯЁа-яё]+(?:-[А-ЯЁа-яё]+)*\.?")
_PATRONYMIC_ENDINGS = ("вич", "вна", "вны", "вне", "вной", "ична", "ичны", "ичне", "ичной", "ич")
# Общие слова должностей не отличают одну должность от другой.
_GENERIC = frozenset(
    {
        "начальник", "заместитель", "главный", "ведущий", "старший", "специалист", "эксперт",
        "отдел", "руководитель", "сотрудник", "работник", "чиновник", "управление", "по",
        "и", "в", "г", "энский", "энск", "область", "город",
    }
)  # fmt: skip


@lru_cache(maxsize=1)
def _morph() -> Any:
    import pymorphy3  # noqa: PLC0415 — тяжёлый словарь грузим один раз и только при надобности

    return pymorphy3.MorphAnalyzer()


@lru_cache(maxsize=20_000)
def lemma(word: str, prefer: str | None = None) -> str:
    """Именительный падеж слова; prefer — граммема pymorphy (Surn, Name, Patr)."""
    lowered = word.lower().replace("ё", "е").strip(".")
    parses = _morph().parse(lowered)
    if prefer:
        preferred = [p for p in parses if prefer in p.tag]
        if preferred:
            return str(preferred[0].normal_form).replace("ё", "е")
    return str(parses[0].normal_form).replace("ё", "е") if parses else lowered


@lru_cache(maxsize=20_000)
def surname_key(word: str) -> str:
    """Ключ фамилии, общий для мужской и женской формы и падежей: «Беловой» → «белов»."""
    lowered = word.lower().replace("ё", "е")
    key = lemma(word, "Surn")
    for female in ("ова", "ева", "ина", "ына"):
        if key.endswith(female):
            key = key[:-1]
    for ending, base in (("овой", "ов"), ("евой", "ев"), ("иной", "ин"), ("ыной", "ын")):
        if lowered.endswith(ending) and not key.endswith(base):
            key = lowered[: -len(ending)] + base
    return key


def _is_patronymic(word: str) -> bool:
    lowered = word.lower()
    return lowered.endswith(_PATRONYMIC_ENDINGS) or "Patr" in _morph().parse(lowered)[0].tag


def _is_given_name(word: str) -> bool:
    return any("Name" in p.tag for p in _morph().parse(word.lower())[:3])


@dataclass(frozen=True)
class Mention:
    surname: str
    name: str | None = None  # нормализованное имя
    patronymic: str | None = None
    initials: tuple[str, ...] = ()


def parse_mention(text: str) -> Mention | None:
    tokens = _WORD.findall(text)
    initials = tuple(t[0].lower() for t in tokens if len(t.rstrip(".")) == 1)
    words = [t.rstrip(".") for t in tokens if len(t.rstrip(".")) > 1]
    if not words:
        return None
    patronymic = next((w for w in words if _is_patronymic(w)), None)
    rest = [w for w in words if w != patronymic]
    surname: str | None = None
    name: str | None = None
    if len(rest) == 1:
        surname = rest[0]
    elif len(rest) >= 2:
        # Реестр: «Фамилия Имя Отчество»; в тексте бывает «Имя Отчество Фамилия».
        if patronymic is not None and words.index(patronymic) < words.index(rest[-1]):
            name, surname = rest[0], rest[-1]
        elif _is_given_name(rest[0]) and not _is_given_name(rest[1]):
            name, surname = rest[0], rest[1]
        else:
            surname, name = rest[0], rest[1]
    if surname is None or len(surname) < 3:
        return None
    return Mention(
        surname=surname_key(surname),
        name=lemma(name, "Name") if name else None,
        patronymic=lemma(patronymic, "Patr") if patronymic else None,
        initials=initials,
    )


@dataclass(frozen=True)
class _Card:
    card: OfficialCard
    surname: str
    name: str
    patronymic: str


def _card(card: OfficialCard) -> _Card:
    parts = card.full_name.split()
    surname = parts[0] if parts else ""
    name = parts[1] if len(parts) > 1 else ""
    patronymic = parts[2] if len(parts) > 2 else ""
    return _Card(
        card,
        surname_key(surname),
        lemma(name, "Name") if name else "",
        lemma(patronymic, "Patr") if patronymic else "",
    )


def _same(a: str, b: str) -> bool:
    return a == b or fuzz.ratio(a, b) >= 85


def _name_part(mention: Mention, official: _Card) -> float | None:
    """1.0 — имя и отчество совпали, 0.8 — инициалы или только имя, 0.5 — ничего не сказано,
    None — противоречие (кандидат исключается)."""
    if mention.name or mention.patronymic:
        if mention.name and not _same(mention.name, official.name):
            return None
        if mention.patronymic and not _same(mention.patronymic, official.patronymic):
            return None
        return 1.0 if mention.name and mention.patronymic else 0.8
    if mention.initials:
        expected = [official.name[:1], official.patronymic[:1]]
        for given, wanted in zip(mention.initials, expected, strict=False):
            if given != wanted:
                return None
        return 0.8 if len(mention.initials) >= 2 else 0.6
    return 0.5


def _lemmas(text: str) -> set[str]:
    return {lemma(w.rstrip(".")) for w in _WORD.findall(text) if len(w.rstrip(".")) > 1}


@dataclass(frozen=True)
class _Context:
    positions: tuple[frozenset[str], ...]  # леммы упомянутых должностей
    organs: frozenset[str]  # органы, названные в тексте


def _post_words(post: OfficialPost) -> set[str]:
    return _lemmas(f"{post.title} {post.department}")


def _position_matches(mentioned: frozenset[str], post: OfficialPost) -> bool:
    """Все отличительные слова упомянутой должности есть в должности служащего."""
    distinctive = {w for w in mentioned if w not in _GENERIC}
    if not distinctive:
        return False
    words = _post_words(post)
    return all(any(_same(w, p) for p in words) for w in distinctive)


def _organs_in(text_lemmas: set[str], organ_names: set[str]) -> frozenset[str]:
    keywords = {organ: _lemmas(organ) - _GENERIC for organ in organ_names}
    found = set()
    for organ, words in keywords.items():
        others = set().union(*(w for o, w in keywords.items() if o != organ)) if keywords else set()
        distinctive = words - others
        if distinctive & text_lemmas:
            found.add(organ)
    return frozenset(found)


class MorphPersonMatcher:
    """Реализует PersonMatcherInterface (pymorphy3 + rapidfuzz)."""

    def match(
        self,
        analysis: AppealAnalysis,
        text: str,
        officials: Sequence[OfficialCard],
        on: date,
    ) -> MatchResult:
        cards = [_card(c) for c in officials]
        organ_names = {p.organ for c in officials for p in c.posts}
        context = _Context(
            positions=tuple(
                frozenset(_lemmas(p)) for p in analysis.mentions_of(EntityType.POSITION)
            ),
            organs=_organs_in(_lemmas(text), organ_names),
        )
        linked: list[UUID] = []
        candidates: dict[UUID, MatchCandidate] = {}
        mentions = [m for m in (parse_mention(t) for t in analysis.person_mentions()) if m]
        for mention in mentions:
            scored = []
            for card in cards:
                score = self._score(mention, card, context)
                if score is not None and score >= CANDIDATE_SCORE:
                    scored.append((score, card))
            strong = [card for score, card in scored if score >= LINK_SCORE]
            if len(strong) == 1:
                linked.append(strong[0].card.id)
                continue
            for score, card in scored:
                _keep(candidates, card.card, score)
        if not mentions:
            for card, score in self._by_position(cards, context, on):
                _keep(candidates, card.card, score)
        linked_ids = tuple(dict.fromkeys(linked))
        return MatchResult(
            linked=linked_ids,
            candidates=tuple(
                sorted(
                    (c for pid, c in candidates.items() if pid not in linked_ids),
                    key=lambda c: -c.score,
                )
            ),
        )

    @staticmethod
    def _score(mention: Mention, card: _Card, context: _Context) -> float | None:
        ratio = fuzz.ratio(mention.surname, card.surname)
        if ratio < SURNAME_THRESHOLD:
            return None
        surname_part = 1.0 if ratio >= 95 else 0.9
        name_part = _name_part(mention, card)
        if name_part is None:
            return None
        posts = card.card.posts
        if any(_position_matches(p, post) for p in context.positions for post in posts):
            context_part = 1.0
        elif context.organs and any(post.organ in context.organs for post in posts):
            context_part = 0.7
        elif context.organs:
            context_part = 0.0
        else:
            context_part = 0.5
        return round(0.5 * surname_part + 0.25 * name_part + 0.25 * context_part, 3)

    @staticmethod
    def _by_position(cards: list[_Card], context: _Context, on: date) -> list[tuple[_Card, float]]:
        found: list[tuple[_Card, float]] = []
        for mentioned in context.positions:
            holders = [
                card
                for card in cards
                for post in card.card.posts
                if post.held_on(on)
                and _position_matches(mentioned, post)
                and (not context.organs or post.organ in context.organs)
            ]
            unique = list({c.card.id: c for c in holders}.values())
            if 0 < len(unique) <= MAX_POSITION_CANDIDATES:
                found += [(card, POSITION_CANDIDATE_SCORE) for card in unique]
        return found


def _keep(candidates: dict[UUID, MatchCandidate], card: OfficialCard, score: float) -> None:
    current = candidates.get(card.id)
    if current is None or current.score < score:
        candidates[card.id] = MatchCandidate(card.id, card.full_name, round(score, 2))
