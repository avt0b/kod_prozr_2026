from dataclasses import dataclass, field
from uuid import NAMESPACE_URL, UUID, uuid5

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
    max_nodes: int = 150
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

    def update_node(self, node: GraphNode) -> None:
        if node.id in self._nodes:
            self._nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """Добавить ребро между узлами графа. Родство симметрично: связь пары людей одна,
        в какую бы сторону её ни прочитали; остаётся первое ребро — со стороны, ближней к корню
        (обход в ширину), с подписью с точки зрения этой стороны."""
        if edge.source not in self._nodes or edge.target not in self._nodes:
            return
        source, target = edge.source, edge.target
        if edge.type is EdgeType.KINSHIP:
            source, target = min(source, target), max(source, target)
        self._edges.setdefault((source, target, edge.type), edge)

    def set_risk(self, scores: dict[UUID, float]) -> None:
        for node_id, node in list(self._nodes.items()):
            if node.type is NodeType.PERSON and node_id in scores:
                self._nodes[node_id] = GraphNode(node.id, node.type, node.label, scores[node_id])

    def ids_of(self, node_type: NodeType) -> list[UUID]:
        return [n.id for n in self._nodes.values() if n.type is node_type]


def contract_group_id(company_id: UUID, organ_id: UUID) -> UUID:
    """Stable node identity shared by graph and risk evidence."""
    return uuid5(NAMESPACE_URL, f"kodprozr:contracts:{company_id}:{organ_id}")
