from typing import Any

import httpx

from src.core.exceptions import ExternalServiceError
from src.core.infrastructure.interfaces.llm_client import ChatMessage, LLMClientInterface
from src.core.infrastructure.logger import get_logger

logger = get_logger(__name__)


class OpenAICompatibleLLMClient(LLMClientInterface):
    """Клиент к любому OpenAI-совместимому API: vLLM, Ollama (`/v1`), облачные провайдеры.

    Ходит в `POST {LLM_BASE_URL}/chat/completions`. SDK openai не тянем — хватает httpx.
    """

    def __init__(self, base_url: str, api_key: str | None, model: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            logger.warning("LLM request failed: {}", type(exc).__name__)
            raise ExternalServiceError(f"LLM is unavailable: {type(exc).__name__}") from exc

        if not isinstance(content, str):
            raise ExternalServiceError("LLM returned empty content")
        return content
