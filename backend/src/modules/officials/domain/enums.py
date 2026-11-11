from enum import StrEnum


class AuthorityKind(StrEnum):
    """Вид полномочий должности (контракт: Authority.kind)."""

    PROCUREMENT = "procurement"
    PERMITS = "permits"
    INSPECTION = "inspection"
    BUDGET = "budget"
    HR = "hr"


class KinshipKind(StrEnum):
    """Степень родства (контракт: Kinship.kind). Значения уходят в API — не переименовывать."""

    SPOUSE = "spouse"
    CHILD = "child"
    PARENT = "parent"
    SIBLING = "sibling"
    IN_LAW = "in_law"
    OTHER = "other"

    def inverse(self) -> "KinshipKind":
        """Родство с точки зрения второго человека: если B — ребёнок A, то A — родитель B."""
        if self is KinshipKind.CHILD:
            return KinshipKind.PARENT
        if self is KinshipKind.PARENT:
            return KinshipKind.CHILD
        return self
