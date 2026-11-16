from uuid import UUID

from src.core.exceptions import DomainValidationError, NotFoundError


class ReportDraftNotFoundError(NotFoundError):
    def __init__(self, report_id: UUID) -> None:
        super().__init__("Черновик докладной не найден")


class ReportSubjectNotFoundError(NotFoundError):
    def __init__(self, person_id: UUID) -> None:
        super().__init__("Служащий не найден")


class EmptyReportTextError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Текст докладной не может быть пустым")
