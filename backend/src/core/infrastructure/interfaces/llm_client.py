from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


class LLMClientInterface(Protocol):
    """Порт к языковой модели. Модули оборачивают его своими адаптерами
    (AppealAnalyzer, ReportWriter, Assistant) и не знают о провайдере.
    """

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> str:
        """Вернуть текст ответа модели. Сбой — ExternalServiceError."""
        ...
