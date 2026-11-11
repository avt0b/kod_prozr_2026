from enum import StrEnum


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RuleCode(StrEnum):
    R01 = "R01"
    R02 = "R02"
    R03 = "R03"
    R04 = "R04"
    R05 = "R05"
    R06 = "R06"
    R07 = "R07"
    R08 = "R08"


class NodeType(StrEnum):
    """Типы узлов графа связей (контракт: /officials/{id}/graph)."""

    PERSON = "person"
    COMPANY = "company"
    ORGAN = "organ"
    CONTRACT = "contract"
    APPEAL = "appeal"


class EdgeType(StrEnum):
    KINSHIP = "kinship"
    FOUNDER = "founder"
    DIRECTOR = "director"
    APPOINTMENT = "appointment"
    EMPLOYMENT = "employment"
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    MENTIONS = "mentions"
