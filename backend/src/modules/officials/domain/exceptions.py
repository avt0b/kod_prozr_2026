from uuid import UUID

from src.core.exceptions import DomainValidationError, NotFoundError


class OfficialNotFoundError(NotFoundError):
    def __init__(self, person_id: UUID) -> None:
        super().__init__(f"Official {person_id} not found (no person or no appointments)")


class OrganNotFoundError(NotFoundError):
    def __init__(self, organ_id: UUID) -> None:
        super().__init__(f"Organ {organ_id} not found")


class InvalidPeriodError(DomainValidationError):
    def __init__(self, message: str = "ended_at must not be earlier than started_at") -> None:
        super().__init__(message)


class SelfKinshipError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("A person cannot be a relative of themselves")
