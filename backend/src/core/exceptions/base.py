class DomainError(Exception):
    """Нарушение бизнес-правила. По умолчанию -> 400."""

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    """Сущность не найдена -> 404."""


class ConflictError(DomainError):
    """Действие недопустимо в текущем состоянии (переход статуса и т.п.) -> 409."""


class DomainValidationError(DomainError):
    """Значение нарушает инвариант предметной области -> 422."""


class InfrastructureError(Exception):
    """Сбой инфраструктуры (БД, сеть). По умолчанию -> 500."""

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)


class ExternalServiceError(InfrastructureError):
    """Внешний сервис (LLM) недоступен или ответил мусором -> 503."""
