import json
from time import perf_counter
from typing import Any

import httpx
from jsonschema import ValidationError, validate

from src.core.exceptions.base import LLMInvalidResponseError, LLMUnavailableError
from src.core.infrastructure.interfaces.llm_client import ChatMessage
from src.core.infrastructure.logger import get_logger

logger = get_logger(__name__)


class OpenAICompatibleLLMClient:
    """OpenAI-compatible transport. One retry for transient transport/server failures."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout: float,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        json_mode: bool = False,
        temperature: float = 0.0,
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
        started = perf_counter()
        client = self._client
        for attempt in range(2):
            try:
                response = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                retryable = not isinstance(exc, httpx.HTTPStatusError) or (
                    exc.response.status_code >= 500 or exc.response.status_code == 429
                )
                logger.warning(
                    "LLM transport failure: {} attempt={}", type(exc).__name__, attempt + 1
                )
                if retryable and attempt == 0:
                    continue
                raise LLMUnavailableError("LLM is unavailable") from exc
            try:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("empty response")
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                raise LLMInvalidResponseError("LLM returned invalid content") from exc
            logger.info(
                "LLM model={} duration_ms={:.1f}",
                self._model,
                (perf_counter() - started) * 1000,
            )
            return content
        raise LLMUnavailableError("LLM is unavailable")

    async def complete_text(self, system: str, messages: list[ChatMessage]) -> str:
        return await self.complete([ChatMessage("system", system), *messages])

    async def complete_json(
        self, system: str, messages: list[ChatMessage], schema: dict[str, Any]
    ) -> dict[str, Any]:
        raw = await self.complete(
            [ChatMessage("system", system + "\nJSON schema:\n" + json.dumps(schema)), *messages],
            json_mode=True,
        )
        try:
            result: object = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError("expected object")
            validate(result, schema)
        except (ValueError, ValidationError) as exc:
            raise LLMInvalidResponseError("LLM JSON failed schema validation") from exc
        return result
