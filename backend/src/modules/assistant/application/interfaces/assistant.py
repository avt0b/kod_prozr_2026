from typing import Protocol

from src.modules.assistant.domain.answer import Answer, Question


class AssistantInterface(Protocol):
    """Порт ассистента аналитика. ADR-11: только ограниченный набор инструментов
    (поиск служащего, флаги, обращения), произвольный SQL не генерируем.

    Сейчас есть только фейк. TODO: LLM-адаптер с tool calling поверх published language
    модулей (QueryOfficialsUseCase, QueryRiskUseCase, QueryAppealsUseCase) через ACL.
    """

    async def ask(self, question: Question) -> Answer: ...
