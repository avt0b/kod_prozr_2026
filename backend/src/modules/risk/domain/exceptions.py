from uuid import UUID

from src.core.exceptions import DomainValidationError, NotFoundError


class RiskSubjectNotFoundError(NotFoundError):
    def __init__(self, person_id: UUID) -> None:
        super().__init__(f"Official {person_id} not found")


class InvalidGraphDepthError(DomainValidationError):
    def __init__(self, depth: int, max_depth: int) -> None:
        super().__init__(f"depth must be within 1..{max_depth}, got {depth}")
