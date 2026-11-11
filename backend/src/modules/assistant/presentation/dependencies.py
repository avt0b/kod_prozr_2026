from typing import Annotated

from fastapi import Depends

from src.modules.assistant.application.interfaces.assistant import AssistantInterface
from src.modules.assistant.application.use_cases.ask_question import AskQuestionUseCase
from src.modules.assistant.infrastructure.adapters.fake_assistant import FakeAssistant


def get_assistant() -> AssistantInterface:
    # TODO: при LLM_BASE_URL — LLM-адаптер с инструментами (порты к officials/risk через src/web).
    return FakeAssistant()


def get_ask_question_use_case(
    assistant: Annotated[AssistantInterface, Depends(get_assistant)],
) -> AskQuestionUseCase:
    return AskQuestionUseCase(assistant)
