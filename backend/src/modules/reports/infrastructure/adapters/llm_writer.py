import re

from src.core.exceptions import ExternalServiceError
from src.core.infrastructure.interfaces.llm_client import ChatMessage, LLMClientInterface
from src.modules.reports.application.interfaces.report_writer import WrittenReport
from src.modules.reports.domain.dossier import Dossier
from src.modules.reports.infrastructure.adapters.template_writer import render_report

SYSTEM_PROMPT = """Ты помогаешь аналитику подразделения по профилактике коррупции.
Перепиши черновик докладной записки официально-деловым стилем, связным текстом.
Строго сохраняй факты, ФИО, суммы, даты и ссылки на нормы. Ничего не добавляй от себя.
Формулируй осторожно: «может свидетельствовать», а не «является нарушением».
Верни только текст докладной записки."""


class LLMReportWriter:
    """Реализует порт ReportWriterInterface: шаблон даёт факты, LLM — стиль.

    Факты не генерируются моделью — она только переписывает шаблонный черновик, поэтому
    галлюцинации ограничены формулировками. Промпт — черновик, финал ведёт Влад О.
    """

    def __init__(self, llm: LLMClientInterface, model_name: str) -> None:
        self._llm = llm
        self._model_name = model_name

    async def write(self, dossier: Dossier) -> WrittenReport:
        draft = render_report(dossier)
        text = await self._llm.complete(
            [
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(role="user", content=draft),
            ],
            temperature=0.2,
        )
        missing, invented = check_facts(draft, text)
        if missing or invented:
            # AI-09: LLM не имеет права терять или придумывать факты — тогда берём шаблон.
            raise ExternalServiceError(
                f"LLM report changed facts: missing {len(missing)}, invented {len(invented)}"
            )
        return WrittenReport(text=text.strip(), generator=f"llm:{self._model_name}")


# ФИО «Соколов А.В.» / «Соколов Андрей Викторович», числа (суммы, даты, ИНН, номера), нормы.
_NAME = re.compile(r"[А-ЯЁ][а-яё]+ (?:[А-ЯЁ]\.\s?[А-ЯЁ]\.|[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+(?:вич|вна))")
_NUMBER = re.compile(r"\d[\d\s.,]*\d|\d")


def _numbers(text: str) -> set[str]:
    return {re.sub(r"\D", "", n) for n in _NUMBER.findall(text)} - {""}


def check_facts(draft: str, text: str) -> tuple[set[str], set[str]]:
    """Факты шаблона, которых нет в тексте LLM, и числа, которых не было в шаблоне."""
    names = set(_NAME.findall(draft))
    missing = {n for n in names if n.split()[0][:-1] not in text}  # фамилия без окончания
    draft_numbers, text_numbers = _numbers(draft), _numbers(text)
    missing |= draft_numbers - text_numbers
    invented = text_numbers - draft_numbers
    return missing, invented
