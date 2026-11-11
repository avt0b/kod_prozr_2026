from uuid import UUID

from src.core.exceptions import ConflictError, DomainValidationError, NotFoundError


class AppealNotFoundError(NotFoundError):
    def __init__(self, appeal_id: UUID) -> None:
        super().__init__(f"Appeal {appeal_id} not found")


class AppealClosedError(ConflictError):
    def __init__(self, appeal_id: UUID) -> None:
        super().__init__(f"Appeal {appeal_id} is closed and cannot be changed")


class InvalidAppealStatusTransitionError(ConflictError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Appeal status cannot change from {current} to {target}")


class EmptyAppealTextError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Appeal text must not be empty")


class InvalidAnalysisError(DomainValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid appeal analysis: {message}")
