from uuid import uuid4

from src.modules.risk.domain.enums import EdgeType, NodeType
from src.modules.risk.domain.graph import ConnectionsGraph, GraphEdge, GraphNode


def _graph() -> tuple[ConnectionsGraph, list[GraphNode]]:
    nodes = [GraphNode(uuid4(), NodeType.PERSON, name) for name in ("Соколов", "Соколова")]
    graph = ConnectionsGraph(root_id=nodes[0].id)
    for node in nodes:
        graph.add_node(node)
    return graph, nodes


def test_kinship_read_from_both_sides_is_one_edge() -> None:
    graph, (official, spouse) = _graph()

    graph.add_edge(GraphEdge(official.id, spouse.id, EdgeType.KINSHIP, "супруг(а)"))
    graph.add_edge(GraphEdge(spouse.id, official.id, EdgeType.KINSHIP, "супруг(а)"))

    assert graph.edges == [GraphEdge(official.id, spouse.id, EdgeType.KINSHIP, "супруг(а)")]


def test_first_kinship_label_wins_for_asymmetric_kinds() -> None:
    graph, (parent, child) = _graph()

    graph.add_edge(GraphEdge(parent.id, child.id, EdgeType.KINSHIP, "ребёнок"))
    graph.add_edge(GraphEdge(child.id, parent.id, EdgeType.KINSHIP, "родитель"))

    assert [(e.source, e.label) for e in graph.edges] == [(parent.id, "ребёнок")]


def test_directed_edges_keep_direction() -> None:
    graph, (a, b) = _graph()

    graph.add_edge(GraphEdge(a.id, b.id, EdgeType.MENTIONS, "упоминает"))
    graph.add_edge(GraphEdge(b.id, a.id, EdgeType.MENTIONS, "упоминает"))

    assert len(graph.edges) == 2
