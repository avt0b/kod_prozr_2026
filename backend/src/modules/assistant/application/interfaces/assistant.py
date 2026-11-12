from typing import Protocol

from src.modules.assistant.domain.answer import Answer, Question


class AssistantInterface(Protocol):
    """Порт ассистента аналитика. ADR-11: только ограниченный набор инструментов
    (поиск служащего, флаги, обращения), произвольный SQL не генерируем.

    ToolAssistant выбирает фиксированный инструмент через LLM или словарную маршрутизацию;
    данные приходят через AssistantToolsInterface и published language модулей.
    """

    async def ask(self, question: Question) -> Answer: ...
