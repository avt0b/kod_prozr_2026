"""Сопоставление упоминания лица в тексте («Иванову И.И.») с ФИО из реестра.

Эвристика без морфологии: основа фамилии (без падежного окончания) + совпадение инициалов.
Хватает для синтетики; для реальных текстов — заменить на pymorphy/natasha (TODO).
"""

import re
from dataclasses import dataclass

_WORD = re.compile(r"[А-ЯЁA-Z][а-яёa-z]+(?:-[А-ЯЁA-Z][а-яёa-z]+)?")
_INITIAL = re.compile(r"\b([А-ЯЁ])\.")
_PATRONYMIC_SUFFIXES = ("вич", "вна", "ична", "чна", "ич")
_CASE_ENDINGS = (
    "ому",
    "ему",
    "ой",
    "ей",
    "ым",
    "им",
    "ом",
    "ем",
    "ую",
    "ою",
    "у",
    "а",
    "е",
    "ы",
    "и",
)
MIN_STEM = 4


@dataclass(frozen=True)
class NameQuery:
    surname_stem: str
    initials: tuple[str, ...]  # первые буквы имени и отчества, если известны
    given_names: tuple[str, ...] = ()


def surname_stem(surname: str) -> str:
    lowered = surname.lower().replace("ё", "е")
    for ending in _CASE_ENDINGS:
        if lowered.endswith(ending) and len(lowered) - len(ending) >= MIN_STEM:
            return lowered[: -len(ending)]
    return lowered


def parse_mention(text: str) -> NameQuery | None:
    words = _WORD.findall(text)
    initials = tuple(_INITIAL.findall(text))
    if not words:
        return None
    if len(words) >= 3 and words[2].lower().endswith(_PATRONYMIC_SUFFIXES):
        # «Иванов Иван Иванович» (в любом падеже): фамилия первая
        return NameQuery(surname_stem(words[0]), (words[1][0], words[2][0]), tuple(words[1:3]))
    # В реестре и извлечённых сущностях фамилия идёт первой, включая падежные ФИО.
    surname = words[0]
    if len(surname) < MIN_STEM:
        return None
    if not initials and len(words) > 1:
        initials = tuple(word[0].upper() for word in words[1:3])
    return NameQuery(surname_stem(surname), initials[:2], tuple(words[1:3]))


def matches(full_name: str, query: NameQuery) -> bool:
    parts = full_name.split()
    if not parts or surname_stem(parts[0]) != query.surname_stem:
        return False
    if query.given_names and any(
        _given_stem(mentioned) != _given_stem(actual)
        for mentioned, actual in zip(query.given_names, parts[1:3])
    ):
        return False
    given = [p[0].upper() for p in parts[1:3]]
    return all(i == g for i, g in zip(query.initials, given, strict=False))


def _given_stem(value: str) -> str:
    lowered = value.lower().replace("ё", "е")
    for ending in (
        "ого",
        "ему",
        "ому",
        "ым",
        "им",
        "ом",
        "ем",
        "ой",
        "ий",
        "ю",
        "я",
        "й",
        "у",
        "а",
        "е",
        "ы",
        "и",
    ):
        if lowered.endswith(ending) and len(lowered) - len(ending) >= 3:
            return lowered[: -len(ending)]
    return lowered
