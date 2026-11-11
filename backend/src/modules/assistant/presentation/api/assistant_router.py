from typing import Annotated

from fastapi import APIRouter, Depends

from src.modules.assistant.application.use_cases.ask_question import AskQuestionUseCase
from src.modules.assistant.presentation.dependencies import get_ask_question_use_case
from src.modules.assistant.presentation.schemas.assistant import AskRequest, AskResponse

router = APIRouter(tags=["Assistant"])


@router.post("/assistant/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    use_case: Annotated[AskQuestionUseCase, Depends(get_ask_question_use_case)],
) -> AskResponse:
    """Вопрос ассистенту аналитика. Сейчас — заглушка (FakeAssistant)."""
    return AskResponse.model_validate(await use_case.execute(body.question))
