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
        return WrittenReport(text=text.strip(), generator=f"llm:{self._model_name}")
