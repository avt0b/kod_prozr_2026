from uuid import UUID

from src.core.exceptions import DomainValidationError

NODE_LIMIT = 50
EDGE_LIMIT = 100


def validate_edge(source: UUID, target: UUID, allowed: set[UUID]) -> None:
    if source == target:
        raise DomainValidationError("Выберите два разных объекта.")
    if source not in allowed or target not in allowed:
        raise DomainValidationError("Один из объектов отсутствует в этой схеме или исходном графе.")
