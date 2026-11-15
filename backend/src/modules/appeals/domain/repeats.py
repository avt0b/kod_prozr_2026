"""Сигнал `repeated_subject` (ai.md §2): тот же служащий или компания уже были в других
обращениях. Считает код по базе обращений, а не анализатор: LLM другие обращения не видит.

Критерии:
- другое обращение поступило раньше текущего, но не раньше чем за REPEAT_WINDOW (12 месяцев);
- у него есть анализ, и в нём либо привязан тот же служащий (`linked_person_ids`, только
  автопривязка — кандидаты «возможно: …» не считаются), либо названа та же компания
  (сущность `organization` с кавычками или организационно-правовой формой).

Учитываются только более ранние обращения, поэтому результат не зависит от порядка разбора
и не меняется при повторном анализе старого обращения.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID

from src.modules.appeals.domain.analysis import (
    SIGNALS,
    AppealAnalysis,
    Signal,
    route_of,
    specificity_of,
)
from src.modules.appeals.domain.enums import EntityType

REPEATED_SUBJECT = "repeated_subject"
REPEAT_WINDOW = timedelta(days=365)

_LEGAL_FORM = re.compile(
    r"^(?:ООО|АО|ПАО|ЗАО|ОАО|НАО|ИП|МУП|ГУП|МКУ|МБУ|ФГУП|ГКУ|ГБУ)\b", re.IGNORECASE
)
_QUOTED = re.compile(r"[«\"“„]([^»\"”“]{2,80})[»\"”“]")
_NOT_WORD = re.compile(r"[^0-9a-zа-я]+")


def company_key(text: str) -> str | None:
    """Ключ компании для сравнения: название в кавычках или после ОПФ, без регистра и знаков.

    «ООО «ДорСтройРесурс»» и «фирма «Дорстройресурс»» дают один ключ. Орган без кавычек и ОПФ
    («департамент строительства») ключа не даёт: иначе повтором стало бы любое обращение в орган.
    """
    raw = text.strip()
    quoted = _QUOTED.search(raw)
    if quoted:
        name = quoted.group(1)
    elif _LEGAL_FORM.match(raw):
        name = _LEGAL_FORM.sub("", raw, count=1)
    else:
        return None
    key = _NOT_WORD.sub("", name.lower().replace("ё", "е"))
    return key if len(key) >= 3 else None


def company_keys(analysis: AppealAnalysis | None) -> frozenset[str]:
    if analysis is None:
        return frozenset()
    keys = (company_key(t) for t in analysis.mentions_of(EntityType.ORGANIZATION))
    return frozenset(k for k in keys if k)


@dataclass(frozen=True)
class PriorAppeal:
    """Другое обращение глазами сигнала: когда поступило, кто привязан, какие компании."""

    id: UUID
    received_at: datetime
    linked_person_ids: tuple[UUID, ...]
    companies: frozenset[str]


@dataclass(frozen=True)
class RepeatedSubject:
    appeal_ids: tuple[UUID, ...]
    person_ids: tuple[UUID, ...]
    companies: tuple[str, ...]

    def signal(self) -> Signal:
        if self.person_ids and self.companies:
            who = "служащий и компания уже упоминались"
        elif self.person_ids:
            who = "служащий уже упоминался"
        else:
            who = "компания уже упоминалась"
        return Signal(
            REPEATED_SUBJECT,
            f"{who} в других обращениях за 12 месяцев: {len(self.appeal_ids)}",
        )


def find_repeats(
    appeal_id: UUID,
    received_at: datetime,
    linked: Sequence[UUID],
    companies: frozenset[str],
    others: Sequence[PriorAppeal],
) -> RepeatedSubject | None:
    """Более ранние обращения в окне REPEAT_WINDOW с тем же служащим или компанией."""
    since = received_at - REPEAT_WINDOW
    people = set(linked)
    appeal_ids: list[UUID] = []
    hit_people: set[UUID] = set()
    hit_companies: set[str] = set()
    for other in others:
        if other.id == appeal_id or not since <= other.received_at < received_at:
            continue
        same_people = people.intersection(other.linked_person_ids)
        same_companies = companies & other.companies
        if same_people or same_companies:
            appeal_ids.append(other.id)
            hit_people |= same_people
            hit_companies |= same_companies
    if not appeal_ids:
        return None
    return RepeatedSubject(
        appeal_ids=tuple(appeal_ids),
        person_ids=tuple(p for p in dict.fromkeys(linked) if p in hit_people),
        companies=tuple(sorted(hit_companies)),
    )


def with_repeated_subject(
    analysis: AppealAnalysis, repeat: RepeatedSubject | None
) -> AppealAnalysis:
    """Ставит или снимает `repeated_subject` и заново считает конкретность и маршрут.

    По формуле ai.md §2 сигнал не меняет ни `specificity`, ни `route_to`: повтор — не
    проверяемый факт из текста, а серию обращений уже учитывает сумма в R07. Пересчёт оставлен,
    чтобы оба поля всегда были функцией итогового набора сигналов.
    """
    signals = [s for s in analysis.signals if s.code != REPEATED_SUBJECT]
    if repeat is not None:
        signals.append(repeat.signal())
    order = list(SIGNALS)
    signals.sort(key=lambda s: order.index(s.code) if s.code in SIGNALS else len(order))
    codes = frozenset(s.code for s in signals)
    specificity = specificity_of(codes)
    return replace(
        analysis,
        signals=tuple(signals),
        specificity=specificity,
        route_to=route_of(analysis.is_corruption, analysis.category, codes, specificity),
    )
