from src.core.exceptions import DomainValidationError


class InvalidShareError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("share must be within 0..100 (percent)")


class InvalidContractAmountError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Contract amount must be non-negative")


class InvalidRolePeriodError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("ended_at must not be earlier than started_at")
