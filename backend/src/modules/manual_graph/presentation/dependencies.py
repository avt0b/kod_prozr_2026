from src.modules.manual_graph.application.reference_graph import ReferenceGraph


def get_reference_graph() -> ReferenceGraph:
    raise NotImplementedError("Reference graph is provided by the composition root")
