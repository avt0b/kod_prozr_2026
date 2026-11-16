"""AI-04: сигнал repeated_subject считает код по другим обращениям (ai.md §2), а не анализатор."""

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4, uuid5

import pytest

from src.core.infrastructure.interfaces.llm_client import ChatMessage
from src.modules.appeals.application.interfaces.person_matcher import OfficialCard, OfficialPost
from src.modules.appeals.application.services.appeal_analysis import AppealAnalysisService
from src.modules.appeals.domain.analysis import SIGNALS
from src.modules.appeals.domain.appeal import Appeal
from src.modules.appeals.domain.repeats import (
    REPEAT_WINDOW,
    REPEATED_SUBJECT,
    PriorAppeal,
    company_key,
    find_repeats,
    with_repeated_subject,
)
from src.modules.appeals.infrastructure.adapters.llm_analyzer import (
    SYSTEM_PROMPT,
    LLMAnswer,
    LLMAppealAnalyzer,
    to_analysis,
)
from src.modules.appeals.infrastructure.adapters.person_matcher import MorphPersonMatcher
from src.modules.appeals.infrastructure.adapters.rule_based_analyzer import (
    RuleBasedAppealAnalyzer,
)

NS = UUID("00000000-0000-0000-0000-0000000000a6")
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
SOKOLOV = uuid5(NS, "sokolov")
OTHER = uuid5(NS, "other")

DEMO = (
    "Начальник отдела закупок Соколов Андрей Викторович отдаёт контракты фирме "
    "«ДорСтройРесурс», которая принадлежит его жене. В марте 2026 года им дали контракт "
    "на 9,5 млн рублей без конкурса."
)
VAGUE = "Соколов Андрей Викторович берёт взятки, все знают. Разберитесь!"


def prior(
    days_ago: float, people: Sequence[UUID] = (), companies: Sequence[str] = ()
) -> PriorAppeal:
    return PriorAppeal(uuid4(), NOW - timedelta(days=days_ago), tuple(people), frozenset(companies))


# ------------------------------------------------------------------ компании
@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("«ДорСтройРесурс»", "дорстройресурс"),
        ("ООО «ДорСтройРесурс»", "дорстройресурс"),
        ('фирма "Дорстройресурс"', "дорстройресурс"),
        ("ООО Вектор-Плюс", "векторплюс"),
        ("АО «Стройснаб-Т»", "стройснабт"),
        ("департамент строительства", None),  # орган, а не компания: не повод для повтора
        ("«Я»", None),
    ],
)
def test_company_key(text: str, key: str | None) -> None:
    assert company_key(text) == key


# ------------------------------------------------------------------ окно и критерии
def test_same_official_in_earlier_appeal_within_window() -> None:
    me = uuid4()
    others = [
        prior(30, [SOKOLOV]),
        prior(200, [SOKOLOV, OTHER]),
        prior(400, [SOKOLOV]),  # старше 12 месяцев
        prior(-5, [SOKOLOV]),  # пришло позже: на этот разбор не влияет
        prior(10, [OTHER]),  # другой служащий
        PriorAppeal(me, NOW - timedelta(days=1), (SOKOLOV,), frozenset()),  # само обращение
    ]
    repeat = find_repeats(me, NOW, [SOKOLOV], frozenset(), others)
    assert repeat is not None
    assert repeat.appeal_ids == (others[0].id, others[1].id)
    assert repeat.person_ids == (SOKOLOV,)
    assert repeat.companies == ()
    signal = repeat.signal()
    assert signal.code == REPEATED_SUBJECT
    assert signal.text == "служащий уже упоминался в других обращениях за 12 месяцев: 2"


def test_window_bounds() -> None:
    edge = prior(REPEAT_WINDOW.days, [SOKOLOV])
    assert find_repeats(uuid4(), NOW, [SOKOLOV], frozenset(), [edge]) is not None
    same_moment = prior(0, [SOKOLOV])
    assert find_repeats(uuid4(), NOW, [SOKOLOV], frozenset(), [same_moment]) is None


def test_same_company_without_official() -> None:
    others = [prior(60, companies=["дорстройресурс"]), prior(60, companies=["вектор"])]
    repeat = find_repeats(uuid4(), NOW, [], frozenset({"дорстройресурс"}), others)
    assert repeat is not None and repeat.companies == ("дорстройресурс",)
    assert repeat.signal().text.startswith("компания уже упоминалась")


def test_no_subjects_no_signal() -> None:
    assert find_repeats(uuid4(), NOW, [], frozenset(), [prior(1, [SOKOLOV])]) is None


# ------------------------------------------------------------------ влияние на анализ
def test_signal_does_not_change_specificity_or_route() -> None:
    vague = RuleBasedAppealAnalyzer().analyze_sync(VAGUE)
    assert "vague_no_facts" in vague.signal_codes
    repeat = find_repeats(uuid4(), NOW, [SOKOLOV], frozenset(), [prior(30, [SOKOLOV])])

    marked = with_repeated_subject(vague, repeat)

    assert REPEATED_SUBJECT in marked.signal_codes
    assert "vague_no_facts" in marked.signal_codes, "повтор — не проверяемый факт из текста"
    assert (marked.specificity, marked.route_to) == (vague.specificity, vague.route_to)
    codes = [s.code for s in marked.signals]
    assert codes == [c for c in SIGNALS if c in codes], "порядок закрытого списка"
    assert REPEATED_SUBJECT not in with_repeated_subject(marked, None).signal_codes


def test_analyzer_cannot_set_repeated_subject() -> None:
    answer = LLMAnswer.model_validate(
        {
            "is_corruption": True,
            "category": "bribe",
            "confidence": 0.9,
            "entities": [{"type": "person", "text": "Соколов Андрей Викторович"}],
            "signals": ["named_official", REPEATED_SUBJECT],
            "summary": "Взятки.",
        }
    )
    analysis = to_analysis(answer, VAGUE, "llm:test")
    assert REPEATED_SUBJECT not in analysis.signal_codes
    assert "vague_no_facts" in analysis.signal_codes
    assert f"- {REPEATED_SUBJECT}" not in SYSTEM_PROMPT


# ------------------------------------------------------------------ сервис: LLM и фоллбэк
class FakeLLM:
    """LLM без сети: отвечает фиксированным JSON и ставит repeated_subject сама —
    код должен его снять и поставить по базе."""

    def __init__(self, answer: dict[str, Any]) -> None:
        self.answer = answer

    async def complete(self, messages: list[ChatMessage], **_: Any) -> str:
        raise NotImplementedError

    async def complete_json(
        self, system: str, messages: list[ChatMessage], schema: dict[str, Any]
    ) -> dict[str, Any]:
        return self.answer

    async def complete_text(self, system: str, messages: list[ChatMessage]) -> str:
        raise NotImplementedError


class FakeDirectory:
    def __init__(self, cards: list[OfficialCard]) -> None:
        self.cards = cards

    async def officials(self) -> list[OfficialCard]:
        return self.cards

    async def get_many(self, ids: Sequence[UUID]) -> list[Any]:
        return []


class FakeRepository:
    def __init__(self, others: list[PriorAppeal]) -> None:
        self.others = others
        self.calls: list[dict[str, Any]] = []

    async def prior_subjects(self, **kwargs: Any) -> list[PriorAppeal]:
        self.calls.append(kwargs)
        return self.others


def service(analyzer: Any, others: list[PriorAppeal]) -> tuple[AppealAnalysisService, Any]:
    post = OfficialPost(
        "Начальник отдела закупок",
        "Отдел закупок",
        "Департамент строительства и дорожного хозяйства",
        date(2020, 1, 1),
        None,
    )
    directory = FakeDirectory([OfficialCard(SOKOLOV, "Соколов Андрей Викторович", (post,))])
    repository = FakeRepository(others)
    return AppealAnalysisService(analyzer, directory, MorphPersonMatcher(), repository), repository  # type: ignore[arg-type]


LLM_ANSWER = {
    "is_corruption": True,
    "category": "conflict_of_interest",
    "confidence": 0.9,
    "entities": [
        {"type": "person", "text": "Соколов Андрей Викторович"},
        {"type": "organization", "text": "«ДорСтройРесурс»"},
    ],
    "signals": ["named_official", "relative_mentioned", REPEATED_SUBJECT],
    "summary": "Контракты фирме жены.",
}


@pytest.mark.parametrize("engine", ["llm", "fallback"])
async def test_service_marks_repeated_subject(engine: str) -> None:
    analyzer = (
        LLMAppealAnalyzer(FakeLLM(LLM_ANSWER), "fake")
        if engine == "llm"
        else RuleBasedAppealAnalyzer()
    )
    earlier = [prior(90, [SOKOLOV]), prior(150, companies=["дорстройресурс"])]
    svc, repository = service(analyzer, earlier)
    appeal = Appeal(text=DEMO, channel="letter", received_at=NOW)

    await svc.analyze(appeal)

    analysis = appeal.analysis
    assert analysis is not None and analysis.engine == engine
    assert appeal.linked_person_ids == (SOKOLOV,)
    signal = next(s for s in analysis.signals if s.code == REPEATED_SUBJECT)
    assert signal.text == "служащий и компания уже упоминались в других обращениях за 12 месяцев: 2"
    (call,) = repository.calls
    assert call["exclude_id"] == appeal.id and call["before"] == NOW
    assert call["since"] == NOW - REPEAT_WINDOW
    assert list(call["person_ids"]) == [SOKOLOV] and call["with_companies"]


@pytest.mark.parametrize("engine", ["llm", "fallback"])
async def test_first_appeal_has_no_repeated_subject(engine: str) -> None:
    analyzer = (
        LLMAppealAnalyzer(FakeLLM(LLM_ANSWER), "fake")
        if engine == "llm"
        else RuleBasedAppealAnalyzer()
    )
    svc, _ = service(analyzer, [prior(30, [OTHER])])
    appeal = Appeal(text=DEMO, channel="letter", received_at=NOW)

    await svc.analyze(appeal)

    assert appeal.analysis is not None
    assert REPEATED_SUBJECT not in appeal.analysis.signal_codes


async def test_no_query_without_subjects() -> None:
    svc, repository = service(RuleBasedAppealAnalyzer(), [prior(1, [SOKOLOV])])
    appeal = Appeal(text="Во дворе не вывозят мусор уже неделю.", channel="web", received_at=NOW)

    await svc.analyze(appeal)

    assert repository.calls == []
    assert appeal.analysis is not None and not appeal.analysis.signal_codes
