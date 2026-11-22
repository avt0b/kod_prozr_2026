from abc import ABC, abstractmethod
from uuid import UUID


class ReferenceGraph(ABC):
    @abstractmethod
    async def node_ids(self, official_id: UUID) -> set[UUID]:
        """Validate the official exists and return the actual source-graph identifiers."""
        raise NotImplementedError
