import json
from collections.abc import Callable

import httpx
import pytest

from src.core.exceptions import ExternalServiceError
from src.core.infrastructure.interfaces.llm_client import ChatMessage
from src.core.infrastructure.llm.null_client import NullLLMClient
from src.core.infrastructure.llm.openai_compatible import OpenAICompatibleLLMClient
from src.modules.appeals.infrastructure.adapters.fallback_analyzer import FallbackAppealAnalyzer
from src.modules.appeals.infrastructure.adapters.llm_analyzer import LLMAppealAnalyzer
from src.modules.appeals.infrastructure.adapters.rule_based_analyzer import RuleBasedAppealAnalyzer


def client_with(handler: Callable[[httpx.Request], httpx.Response]) -> OpenAICompatibleLLMClient:
    return OpenAICompatibleLLMClient(
        "https://llm.test/v1",
        None,
        "test",
        1,
        transport=httpx.MockTransport(handler),
    )


async def test_retries_server_failure_once() -> None:
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    assert await client_with(respond).complete_text("system", [ChatMessage("user", "test")]) == "ok"
    assert calls == 2


async def test_invalid_json_retries_then_falls_back() -> None:
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"choices": [{"message": {"content": "[]"}}]})

    analyzer = FallbackAppealAnalyzer(
        LLMAppealAnalyzer(client_with(respond), "test"), RuleBasedAppealAnalyzer()
    )
    analysis = await analyzer.analyze("Иванов П.С. требует взятку 5000 рублей.")
    assert analysis.is_corruption
    assert calls == 2


async def test_schema_is_validated() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["temperature"] == 0
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"score": 2}'}}]})

    with pytest.raises(ExternalServiceError):
        await client_with(respond).complete_json(
            "system", [], {"type": "object", "properties": {"score": {"maximum": 1}}}
        )


async def test_disabled_llm_uses_fallback() -> None:
    analyzer = FallbackAppealAnalyzer(
        LLMAppealAnalyzer(NullLLMClient(), "disabled"), RuleBasedAppealAnalyzer()
    )
    assert (await analyzer.analyze("Не вывозят мусор во дворе")).is_corruption is False


def test_connect_timeout_is_short_and_read_timeout_is_long() -> None:
    client = OpenAICompatibleLLMClient("https://llm.test/v1", None, "test", 90, connect_timeout=3)
    timeout = client._client.timeout
    assert timeout.connect == 3
    assert timeout.read == 90


async def test_unreachable_llm_is_not_retried_and_falls_back() -> None:
    """DROP на файрволе: ConnectTimeout после короткого connect-timeout, без повтора."""
    calls = 0
    seen: list[dict[str, float]] = []

    def drop(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        seen.append(request.extensions["timeout"])
        raise httpx.ConnectTimeout("dropped", request=request)

    llm = OpenAICompatibleLLMClient(
        "https://llm.test/v1",
        None,
        "test",
        90,
        connect_timeout=2,
        transport=httpx.MockTransport(drop),
    )
    analyzer = FallbackAppealAnalyzer(LLMAppealAnalyzer(llm, "test"), RuleBasedAppealAnalyzer())
    analysis = await analyzer.analyze("Иванов П.С. требует взятку 5000 рублей.")
    assert analysis.is_corruption
    assert analysis.engine == "fallback"
    assert calls == 1
    assert seen[0]["connect"] == 2
    assert seen[0]["read"] == 90


@pytest.mark.parametrize(
    "error", [httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout]
)
async def test_connect_failures_and_timeouts_are_not_retried(
    error: type[httpx.TransportError],
) -> None:
    calls = 0

    def fail(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise error("failed", request=request)

    with pytest.raises(ExternalServiceError):
        await client_with(fail).complete_text("system", [ChatMessage("user", "test")])
    assert calls == 1


async def test_broken_connection_is_retried_once() -> None:
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.RemoteProtocolError("connection reset", request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    assert await client_with(respond).complete_text("system", [ChatMessage("user", "test")]) == "ok"
    assert calls == 2
