from typing import Annotated

from fastapi import Depends

from src.core.infrastructure.dependencies import get_llm_client
from src.core.infrastructure.interfaces.llm_client import LLMClientInterface
from src.modules.assistant.application.interfaces.assistant import AssistantInterface
from src.modules.assistant.application.interfaces.tools import AssistantToolsInterface
from src.modules.assistant.application.use_cases.ask_question import AskQuestionUseCase
from src.modules.assistant.infrastructure.adapters.tool_assistant import ToolAssistant


def get_assistant_tools() -> AssistantToolsInterface:
    raise NotImplementedError("Overridden by composition root")


def get_assistant(
    tools: Annotated[AssistantToolsInterface, Depends(get_assistant_tools)],
    llm: Annotated[LLMClientInterface | None, Depends(get_llm_client)],
) -> AssistantInterface:
    return ToolAssistant(tools, llm)


def get_ask_question_use_case(
    assistant: Annotated[AssistantInterface, Depends(get_assistant)],
) -> AskQuestionUseCase:
    return AskQuestionUseCase(assistant)
