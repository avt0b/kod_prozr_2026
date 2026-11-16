from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

ToolName = Literal[
    "search_officials",
    "get_profile",
    "relatives_among_suppliers",
    "top_risk",
    "find_appeals",
    "company_lookup",
]


@dataclass(frozen=True)
class ToolArguments:
    query: str | None = None
    person_id: UUID | None = None
    organ_id: UUID | None = None
    organ_query: str | None = None
    inn: str | None = None
    min_score: float | None = None
    category: str | None = None
    status: str | None = None
    limit: int = 20


@dataclass(frozen=True)
class ToolItem:
    type: str
    id: str
    label: str
    detail: str


class AssistantToolsInterface(Protocol):
    async def execute(self, tool: ToolName, args: ToolArguments) -> list[ToolItem]: ...
