"""AI-05: сопоставление упомянутых лиц с профилями служащих (ai.md §3)."""

from dataclasses import replace
from datetime import date
from uuid import UUID, uuid5

import pytest

from src.modules.appeals.application.interfaces.person_matcher import OfficialCard, OfficialPost
from src.modules.appeals.domain.analysis import ExtractedEntity
from src.modules.appeals.domain.enums import EntityType
from src.modules.appeals.infrastructure.adapters.person_matcher import (
    MorphPersonMatcher,
    parse_mention,
)
from src.modules.appeals.infrastructure.adapters.rule_based_analyzer import (
    RuleBasedAppealAnalyzer,
)

NS = UUID("00000000-0000-0000-0000-0000000000a5")
O1 = "Департамент строительства и дорожного хозяйства Энской области"
O3 = "Управление ЖКХ и благоустройства г. Энска"
DAY = date(2026, 5, 1)


def card(name: str, title: str, department: str, organ: str = O1) -> OfficialCard:
    post = OfficialPost(title, department, organ, date(2020, 1, 1), None)
    return OfficialCard(uuid5(NS, name), name, (post,))


SOKOLOV = card("Соколов Андрей Викторович", "Начальник отдела закупок", "Отдел закупок")
OFFICIALS = [
    SOKOLOV,
    card("Соколов Пётр Иванович", "Главный специалист", "Юридический отдел", O3),
    card("Иванов Олег Петрович", "Главный специалист", "Отдел дорожного хозяйства"),
    card("Иванов Дмитрий Сергеевич", "Главный специалист", "Отдел капитального строительства"),
    card("Белова Ирина Андреевна", "Начальник отдела благоустройства", "Отдел благоустройства", O3),
]


def match(text: str) -> tuple[set[str], set[str]]:
    analysis = RuleBasedAppealAnalyzer().analyze_sync(text)
    result = MorphPersonMatcher().match(analysis, text, OFFICIALS, DAY)
    names = {c.id: c.full_name for c in OFFICIALS}
    return {names[p] for p in result.linked}, {c.full_name for c in result.candidates}


@pytest.mark.parametrize(
    "text",
    [
        "Начальник отдела закупок Соколов Андрей Викторович берёт откаты.",
        "Прошу проверить Андрея Викторовича Соколова, он берёт взятки.",
        "Жалоба по Соколову Андрею Викторовичу: подрядчики одни и те же.",
        "Начальник отдела закупок Соколов А. В. берёт откаты.",
        "Начальник отдела закупок Саколов А. В. отдаёт контракты своим.",
    ],
)
def test_links_sokolov_in_any_case_and_with_typo(text: str) -> None:
    linked, _ = match(text)
    assert linked == {"Соколов Андрей Викторович"}


def test_contradicting_initials_do_not_link() -> None:
    linked, candidates = match("Соколов П. И. из управления ЖКХ требует взятку 5000 рублей.")
    assert linked == {"Соколов Пётр Иванович"}
    assert "Соколов Андрей Викторович" not in candidates


def test_namesakes_by_surname_only_are_candidates() -> None:
    analysis = RuleBasedAppealAnalyzer().analyze_sync("x")
    text = "Сотрудник департамента строительства Иванов требует деньги."
    start = text.index("Иванов")
    analysis = replace(
        analysis, entities=(ExtractedEntity(EntityType.PERSON, "Иванов", start, start + 6),)
    )
    result = MorphPersonMatcher().match(analysis, text, OFFICIALS, DAY)
    assert result.linked == ()
    assert {c.full_name for c in result.candidates} == {
        "Иванов Олег Петрович",
        "Иванов Дмитрий Сергеевич",
    }


def test_position_only_gives_candidate_without_link() -> None:
    linked, candidates = match(
        "Начальник отдела благоустройства управления ЖКХ отдаёт уборку одной фирме."
    )
    assert linked == set()
    assert candidates == {"Белова Ирина Андреевна"}


def test_female_surname_in_genitive() -> None:
    parsed = parse_mention("Беловой Ирины Андреевны")
    assert parsed is not None and parsed.surname == "белов"
    linked, _ = match("Прошу проверить действия Беловой Ирины Андреевны.")
    assert linked == {"Белова Ирина Андреевна"}
