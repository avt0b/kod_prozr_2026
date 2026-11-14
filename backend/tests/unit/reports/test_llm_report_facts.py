"""AI-09: LLM-текст докладной не теряет и не придумывает факты шаблона."""

from src.modules.reports.infrastructure.adapters.llm_writer import check_facts

DRAFT = (
    "Соколов А.В. замещает должность начальника отдела закупок. ООО «ДорСтройРесурс» "
    "получило 5 контрактов на 38 000 000 руб., последний — 17.03.2026."
)


def test_faithful_rewrite_passes() -> None:
    text = (
        "Установлено, что Соколовым А.В., начальником отдела закупок, компании "
        "«ДорСтройРесурс» переданы 5 контрактов на общую сумму 38 000 000 руб. "
        "(последний от 17.03.2026)."
    )
    assert check_facts(DRAFT, text) == (set(), set())


def test_lost_or_invented_facts_are_reported() -> None:
    missing, invented = check_facts(DRAFT, "Соколов А.В. получил 7 контрактов на 50 млн руб.")
    assert "38000000" in missing and "17032026" in missing
    assert {"7", "50"} <= invented
