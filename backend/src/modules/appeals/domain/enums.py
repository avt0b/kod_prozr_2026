from enum import StrEnum


class AppealStatus(StrEnum):
    NEW = "new"
    ANALYZED = "analyzed"
    ROUTED = "routed"
    CLOSED = "closed"


class AppealCategory(StrEnum):
    BRIBE = "bribe"
    CONFLICT_OF_INTEREST = "conflict_of_interest"
    PROCUREMENT = "procurement"
    ABUSE_OF_POWER = "abuse_of_power"
    OTHER = "other"


class EntityType(StrEnum):
    PERSON = "person"
    ORGANIZATION = "organization"
    POSITION = "position"
    MONEY = "money"
    DATE = "date"
    ADDRESS = "address"
