from typing import Annotated
from uuid import UUID

from fastapi import Depends

from src.modules.manual_graph.application.reference_graph import ReferenceGraph
from src.modules.risk.application.use_cases.get_official_graph import GetOfficialGraphUseCase
from src.modules.risk.presentation.dependencies import get_official_graph_use_case


class OfficialReferenceGraph(ReferenceGraph):
    def __init__(self, graph: GetOfficialGraphUseCase) -> None:
        self.graph = graph

    async def node_ids(self, official_id: UUID) -> set[UUID]:
        graph = await self.graph.execute(official_id, 2)
        return {node.id for node in graph.nodes}


def reference_graph(
    graph: Annotated[GetOfficialGraphUseCase, Depends(get_official_graph_use_case)],
) -> ReferenceGraph:
    return OfficialReferenceGraph(graph)
