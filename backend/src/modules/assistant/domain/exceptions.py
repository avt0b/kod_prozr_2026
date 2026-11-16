from src.core.exceptions import DomainValidationError


class EmptyQuestionError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Вопрос не может быть пустым")
