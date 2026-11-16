from uuid import UUID

from src.core.exceptions import DomainValidationError, NotFoundError


class OfficialNotFoundError(NotFoundError):
    def __init__(self, person_id: UUID) -> None:
        super().__init__("Служащий не найден")


class OrganNotFoundError(NotFoundError):
    def __init__(self, organ_id: UUID) -> None:
        super().__init__("Орган не найден")


class InvalidPeriodError(DomainValidationError):
    def __init__(self, message: str = "Дата окончания не может быть раньше даты начала") -> None:
        super().__init__(message)


class SelfKinshipError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Человек не может быть родственником самому себе")
