from enum import StrEnum


class CompanyStatus(StrEnum):
    """Статус юрлица по ЕГРЮЛ (контракт: Company.status; набор значений уточнён здесь)."""

    ACTIVE = "active"
    LIQUIDATING = "liquidating"
    LIQUIDATED = "liquidated"
    BANKRUPT = "bankrupt"
    REORGANIZING = "reorganizing"


class CompanyRoleKind(StrEnum):
    FOUNDER = "founder"
    DIRECTOR = "director"
