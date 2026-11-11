from dataclasses import dataclass

from src.modules.assistant.application.interfaces.assistant import AssistantInterface
from src.modules.assistant.domain.answer import Question


@dataclass(frozen=True)
class SourceDTO:
    type: str
    id: str
    label: str


@dataclass(frozen=True)
class AnswerDTO:
    answer: str
    sources: tuple[SourceDTO, ...]


class AskQuestionUseCase:
    def __init__(self, assistant: AssistantInterface) -> None:
        self._assistant = assistant

    async def execute(self, question: str) -> AnswerDTO:
        answer = await self._assistant.ask(Question(question.strip()))
        return AnswerDTO(
            answer=answer.answer,
            sources=tuple(SourceDTO(s.type, s.id, s.label) for s in answer.sources),
        )
