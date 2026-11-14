import type { GraphEdge, OfficialGraph } from '@/shared/api';

/** Horizontal levels keep H1's wide first neighbourhood readable on a laptop. */
export function compactPositions(
  graph: OfficialGraph,
  rootId?: string,
  highlight: string[] = [],
): Record<string, { x: number; y: number }> {
  if (highlight.length) {
    const ids = new Set(highlight);
    return {
      ...compactPositions(graph, rootId),
      ...compactPositions(
        {
          nodes: graph.nodes.filter((n) => ids.has(n.id)),
          edges: graph.edges.filter((e) => evidenceEdge(e, ids, graph)),
        },
        rootId,
      ),
    };
  }
  const root = rootId ?? graph.nodes[0]?.id;
  const distances = new Map<string, number>();
  if (root) distances.set(root, 0);
  const queue = root ? [root] : [];
  for (let i = 0; i < queue.length; i++) {
    const id = queue[i];
    for (const edge of graph.edges) {
      const next = edge.source === id ? edge.target : edge.target === id ? edge.source : null;
      if (next && !distances.has(next)) {
        distances.set(next, distances.get(id)! + 1);
        queue.push(next);
      }
    }
  }
  const levels = new Map<number, string[]>();
  for (const node of graph.nodes) {
    const level = distances.get(node.id) ?? 0;
    levels.set(level, [...(levels.get(level) ?? []), node.id]);
  }
  return Object.fromEntries(
    [...levels].flatMap(([level, ids]) =>
      ids.map((id, i) => [id, { x: level * 165, y: (i - (ids.length - 1) / 2) * 100 }]),
    ),
  );
}

/** Evidence describes a subgraph; the employment shortcut is outside an R01 chain. */
export function evidenceEdge(edge: GraphEdge, ids: Set<string>, graph: OfficialGraph): boolean {
  if (!ids.has(edge.source) || !ids.has(edge.target)) return false;
  const hasContracts = graph.nodes.some((n) => n.type === 'contract' && ids.has(n.id));
  return !(hasContracts && ['works_in', 'appointment'].includes(edge.type));
}

export function graphElements(graph: OfficialGraph, rootId?: string) {
  const ids = new Set(graph.nodes.map((n) => n.id));
  return [
    ...graph.nodes.map((node) => ({
      data: { ...node, risk: node.risk ?? undefined },
      classes: node.id === rootId ? 'root' : undefined,
    })),
    ...graph.edges
      .filter((e) => ids.has(e.source) && ids.has(e.target))
      .map((edge, i) => ({
        data: { ...edge, id: `edge:${i}:${edge.source}:${edge.target}` },
      })),
  ];
}
