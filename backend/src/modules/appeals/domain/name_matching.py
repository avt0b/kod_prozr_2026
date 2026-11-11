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


def surname_stem(surname: str) -> str:
    lowered = surname.lower()
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
        return NameQuery(surname_stem(words[0]), (words[1][0], words[2][0]))
    surname = max(words, key=len)
    if len(surname) < MIN_STEM:
        return None
    return NameQuery(surname_stem(surname), initials[:2])


def matches(full_name: str, query: NameQuery) -> bool:
    parts = full_name.split()
    if not parts or not parts[0].lower().startswith(query.surname_stem):
        return False
    given = [p[0].upper() for p in parts[1:3]]
    return all(i == g for i, g in zip(query.initials, given, strict=False))
