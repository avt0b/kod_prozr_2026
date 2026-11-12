import json
from unittest.mock import AsyncMock

import httpx

from src.core.infrastructure.llm.openai_compatible import OpenAICompatibleLLMClient
from src.modules.assistant.application.interfaces.tools import ToolItem
from src.modules.assistant.domain.answer import Question
from src.modules.assistant.infrastructure.adapters.tool_assistant import ToolAssistant


async def test_sources_and_answer_come_from_tool_results_only() -> None:
    tools = AsyncMock()
    tools.execute.return_value = [ToolItem("person", "real-person", "Иванов", "риск 20/100")]

    def reply(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"tool": "top_risk", "args": {"limit": 1}})}}
                ]
            },
        )

    llm = OpenAICompatibleLLMClient(
        "https://llm.test/v1", None, "test", 1, transport=httpx.MockTransport(reply)
    )
    try:
        answer = await ToolAssistant(tools, llm).ask(Question("Кто с самым высоким риском?"))
        assert answer.sources[0].id == "real-person"
        assert "риск 20/100" in answer.answer
        assert tools.execute.call_args.args[1].limit == 1
    finally:
        await llm.aclose()


async def test_unknown_sql_tool_is_rejected_before_execution() -> None:
    tools = AsyncMock()
    calls = 0

    def reply(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "tool": "run_sql",
                                    "args": {"sql": "SELECT secret"},
                                    "sources": ["fabricated"],
                                }
                            )
                        }
                    }
                ]
            },
        )

    llm = OpenAICompatibleLLMClient(
        "https://llm.test/v1", None, "test", 1, transport=httpx.MockTransport(reply)
    )
    try:
        answer = await ToolAssistant(tools, llm).ask(Question("Сколько звёзд в небе?"))
        assert answer.sources == ()
        tools.execute.assert_not_called()
        assert calls == 2
    finally:
        await llm.aclose()


async def test_write_request_never_reaches_tools_or_model() -> None:
    tools, llm = AsyncMock(), AsyncMock()
    answer = await ToolAssistant(tools, llm).ask(Question("Удали всех служащих"))
    assert answer.sources == ()
    tools.execute.assert_not_called()
    llm.complete_json.assert_not_called()


async def test_llm_failure_uses_read_tool_fallback_with_bounded_limit() -> None:
    tools = AsyncMock()
    tools.execute.return_value = []
    # NullLLMClient raises the same controlled availability error as failed transport.
    from_client = OpenAICompatibleLLMClient(
        "https://llm.test/v1",
        None,
        "test",
        1,
        transport=httpx.MockTransport(lambda request: httpx.Response(503)),
    )
    try:
        await ToolAssistant(tools, from_client).ask(Question("Покажи топ 1000 служащих"))
        assert tools.execute.call_args.args[0] == "top_risk"
        assert tools.execute.call_args.args[1].limit == 20
    finally:
        await from_client.aclose()


async def test_planner_cannot_invent_person_ids() -> None:
    tools = AsyncMock()
    tools.execute.return_value = []

    def reply(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "tool": "get_profile",
                                    "args": {"person_id": "b18c4ca3-30e2-56e4-a971-ef71f56e305c"},
                                }
                            )
                        }
                    }
                ]
            },
        )

    llm = OpenAICompatibleLLMClient(
        "https://llm.test/v1", None, "test", 1, transport=httpx.MockTransport(reply)
    )
    try:
        await ToolAssistant(tools, llm).ask(Question("Кто с самым высоким риском?"))
        assert tools.execute.call_args.args[0] == "top_risk"
        assert tools.execute.call_args.args[1].person_id is None
    finally:
        await llm.aclose()
