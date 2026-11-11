from uuid import UUID

from src.core.exceptions import DomainValidationError, NotFoundError


class ReportDraftNotFoundError(NotFoundError):
    def __init__(self, report_id: UUID) -> None:
        super().__init__(f"Report draft {report_id} not found")


class ReportSubjectNotFoundError(NotFoundError):
    def __init__(self, person_id: UUID) -> None:
        super().__init__(f"Official {person_id} not found")


class EmptyReportTextError(DomainValidationError):
    def __init__(self) -> None:
        super().__init__("Report text must not be empty")
