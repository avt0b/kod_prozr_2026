"""Вариант D: коррупционные риски должности по её полномочиям, без персональных данных.

Каталог типовых рисков — экспертная таблица: вид полномочия (`Authority.kind`) → схемы,
которые это полномочие делает возможными, правила R01–R08, которыми система их ищет,
и норма. Уровень риска должности считается только по полномочиям и перечню
коррупционно-опасных должностей: это свойство должности, а не служащего на ней.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class PositionRiskLevel(StrEnum):
    """Уровень коррупционного риска должности. Значения уходят в API — не переименовывать."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class TypicalRisk:
    """Типовой коррупционный риск полномочия."""

    code: str
    title: str
    description: str
    authority: str  # вид полномочия: procurement | permits | inspection | budget | hr
    rule_codes: tuple[str, ...]  # правила, которыми система ищет этот риск; пусто — не ищет
    legal_ref: str


_CATALOG: dict[str, tuple[TypicalRisk, ...]] = {
    "procurement": (
        TypicalRisk(
            code="procurement_affiliated_supplier",
            title="Аффилированный поставщик",
            description="Контракты органа получает компания служащего, его родственника "
            "или бывшего работодателя",
            authority="procurement",
            rule_codes=("R01", "R03", "R05"),
            legal_ref="273-ФЗ ст. 10, 11; 44-ФЗ ст. 31 ч. 1 п. 9",
        ),
        TypicalRisk(
            code="procurement_supplier_capture",
            title="«Свой» поставщик",
            description="Закупки в сфере полномочий раз за разом достаются одному поставщику",
            authority="procurement",
            rule_codes=("R06",),
            legal_ref="273-ФЗ ст. 10",
        ),
        TypicalRisk(
            code="procurement_revolving_door",
            title="Переход к подрядчику",
            description="После увольнения служащий уходит в компанию, с которой заключал контракты",
            authority="procurement",
            rule_codes=("R04",),
            legal_ref="273-ФЗ ст. 12",
        ),
    ),
    "permits": (
        TypicalRisk(
            code="permits_affiliated_applicant",
            title="Разрешения «своим»",
            description="Разрешения и лицензии получают компании, в которых участвует служащий "
            "или его родственники",
            authority="permits",
            rule_codes=("R02", "R05"),
            legal_ref="273-ФЗ ст. 10, 11; 79-ФЗ ст. 17",
        ),
        TypicalRisk(
            code="permits_extortion",
            title="Вымогательство при выдаче разрешений",
            description="Затягивание сроков и отказы ради незаконного вознаграждения",
            authority="permits",
            rule_codes=("R07",),
            legal_ref="УК РФ ст. 290",
        ),
    ),
    "inspection": (
        TypicalRisk(
            code="inspection_loyalty",
            title="Лояльность к проверяемым",
            description="Проверяемая организация связана со служащим или берёт его на работу "
            "после увольнения",
            authority="inspection",
            rule_codes=("R02", "R04"),
            legal_ref="273-ФЗ ст. 10, 12",
        ),
        TypicalRisk(
            code="inspection_extortion",
            title="Вымогательство при проверках",
            description="Угроза санкциями по итогам проверки ради вознаграждения",
            authority="inspection",
            rule_codes=("R07",),
            legal_ref="УК РФ ст. 290",
        ),
    ),
    "budget": (
        TypicalRisk(
            code="budget_affiliated_recipient",
            title="Бюджетные средства аффилированным лицам",
            description="Субсидии и платежи направляются организациям, связанным со служащим",
            authority="budget",
            rule_codes=("R02", "R05"),
            legal_ref="273-ФЗ ст. 10; БК РФ ст. 306.4",
        ),
    ),
    "hr": (
        TypicalRisk(
            code="hr_nepotism",
            title="Протекционизм при найме",
            description="Приём и продвижение родственников и близких лиц, служба в "
            "непосредственной подчинённости родственнику",
            authority="hr",
            rule_codes=(),
            legal_ref="79-ФЗ ст. 16 ч. 1 п. 5",
        ),
    ),
}

# Полномочия, при которых служащий сам решает в пользу внешних лиц (контракт, разрешение,
# итог проверки), — высокий уровень. Бюджет и кадры влияют косвенно — средний.
_DIRECT_DECISION = frozenset({"procurement", "permits", "inspection"})
_INDIRECT_DECISION = frozenset({"budget", "hr"})


def typical_risks(authority_kinds: Iterable[str]) -> tuple[TypicalRisk, ...]:
    """Типовые риски должности в порядке каталога, без повторов."""
    kinds = set(authority_kinds)
    return tuple(risk for kind, risks in _CATALOG.items() if kind in kinds for risk in risks)


def position_risk_level(
    authority_kinds: Iterable[str], is_corruption_risky: bool
) -> PositionRiskLevel:
    """Уровень риска должности по полномочиям и перечню коррупционно-опасных должностей."""
    kinds = set(authority_kinds)
    if kinds & _DIRECT_DECISION:
        return PositionRiskLevel.HIGH
    if kinds & _INDIRECT_DECISION or is_corruption_risky:
        return PositionRiskLevel.MEDIUM
    return PositionRiskLevel.LOW
