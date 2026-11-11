from uuid import UUID

from src.core.exceptions import ConflictError, DomainValidationError, NotFoundError


class AppealNotFoundError(NotFoundError):
    def __init__(self, appeal_id: UUID) -> None:
        super().__init__("Обращение не найдено")


class AppealClosedError(ConflictError):
    def __init__(self, appeal_id: UUID) -> None:
        super().__init__("Обращение закрыто, изменить его нельзя")


class InvalidAppealStatusTransitionError(ConflictError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Недопустимый переход статуса обращения: {current} → {target}")


class EmptyAppealTextError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Текст обращения не может быть пустым")


class InvalidAnalysisError(DomainValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(f"Некорректный анализ обращения: {message}")
