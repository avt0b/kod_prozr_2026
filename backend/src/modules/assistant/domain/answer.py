from dataclasses import dataclass, field

from src.modules.assistant.domain.exceptions import EmptyQuestionError

MAX_QUESTION_LENGTH = 2000


@dataclass(frozen=True)
class Question:
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise EmptyQuestionError()


@dataclass(frozen=True)
class Source:
    """На что опирается ответ: type — person|company|organ|contract|appeal|flag."""

    type: str
    id: str
    label: str


@dataclass(frozen=True)
class Answer:
    answer: str
    sources: tuple[Source, ...] = field(default_factory=tuple)
