from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.modules.officials.domain.enums import AuthorityKind
from src.modules.officials.domain.value_objects import AuthorityScope


@dataclass
class Organ:
    """Государственный (муниципальный) орган."""

    name: str
    inn: str
    region: str
    id: UUID = field(default_factory=uuid4)


@dataclass
class Position:
    """Должность в органе. is_corruption_risky — входит в перечень коррупционно-опасных."""

    organ_id: UUID
    title: str
    department: str
    is_corruption_risky: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass
class Authority:
    """Полномочие, закреплённое за должностью."""

    position_id: UUID
    kind: AuthorityKind
    scope: AuthorityScope = field(default_factory=AuthorityScope)
    id: UUID = field(default_factory=uuid4)
