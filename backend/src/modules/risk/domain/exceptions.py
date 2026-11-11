from uuid import UUID

from src.core.exceptions import DomainValidationError, NotFoundError


class RiskSubjectNotFoundError(NotFoundError):
    def __init__(self, person_id: UUID) -> None:
        super().__init__("Служащий не найден")


class InvalidGraphDepthError(DomainValidationError):
    def __init__(self, depth: int, max_depth: int) -> None:
        super().__init__(f"Глубина графа должна быть от 1 до {max_depth}, передано {depth}")
