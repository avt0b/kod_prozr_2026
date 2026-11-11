from src.core.exceptions import DomainValidationError


class InvalidShareError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Доля должна быть в пределах 0–100 %")


class InvalidContractAmountError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Сумма контракта не может быть отрицательной")


class InvalidRolePeriodError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Дата окончания не может быть раньше даты начала")
