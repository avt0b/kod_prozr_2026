from dataclasses import dataclass, field
from uuid import UUID

from src.modules.risk.domain.enums import EdgeType, NodeType


@dataclass(frozen=True)
class GraphNode:
    id: UUID
    type: NodeType
    label: str
    risk: float | None = None


@dataclass(frozen=True)
class GraphEdge:
    source: UUID
    target: UUID
    type: EdgeType
    label: str


@dataclass
class ConnectionsGraph:
    """Граф связей служащего. Узлы и рёбра без дублей, размер ограничен max_nodes."""

    root_id: UUID
    max_nodes: int = 300
    _nodes: dict[UUID, GraphNode] = field(default_factory=dict)
    _edges: dict[tuple[UUID, UUID, EdgeType], GraphEdge] = field(default_factory=dict)
    truncated: bool = False

    @property
    def nodes(self) -> list[GraphNode]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[GraphEdge]:
        return list(self._edges.values())

    def has(self, node_id: UUID) -> bool:
        return node_id in self._nodes

    def add_node(self, node: GraphNode) -> bool:
        """True, если узел новый и добавлен. При переполнении граф помечается truncated."""
        if node.id in self._nodes:
            return False
        if len(self._nodes) >= self.max_nodes:
            self.truncated = True
            return False
        self._nodes[node.id] = node
        return True

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.source in self._nodes and edge.target in self._nodes:
            self._edges.setdefault((edge.source, edge.target, edge.type), edge)

    def set_risk(self, scores: dict[UUID, float]) -> None:
        for node_id, node in list(self._nodes.items()):
            if node.type is NodeType.PERSON and node_id in scores:
                self._nodes[node_id] = GraphNode(node.id, node.type, node.label, scores[node_id])

    def ids_of(self, node_type: NodeType) -> list[UUID]:
        return [n.id for n in self._nodes.values() if n.type is node_type]
