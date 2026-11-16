from typing import Any

from src.core.exceptions.base import LLMUnavailableError
from src.core.infrastructure.interfaces.llm_client import ChatMessage


class NullLLMClient:
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        json_mode: bool = False,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        raise LLMUnavailableError("LLM is disabled")

    async def complete_json(
        self, system: str, messages: list[ChatMessage], schema: dict[str, Any]
    ) -> dict[str, Any]:
        raise LLMUnavailableError("LLM is disabled")

    async def complete_text(self, system: str, messages: list[ChatMessage]) -> str:
        raise LLMUnavailableError("LLM is disabled")
