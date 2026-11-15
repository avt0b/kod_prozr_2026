import type { GraphEdge, OfficialGraph } from '@/shared/api';

/** Шаг раскладки «по уровням», px: между уровнями, между колонками одного уровня, между строками. */
const LEVEL_GAP = 165;
const SUB_COL_GAP = 140;
const ROW_GAP = 100;
const MAX_ROWS = 5;

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
  // Широкий уровень (у H1 9 соседей) переносим в несколько колонок: иначе граф вытягивается
  // в узкий столбец, вписывается в контейнер с мелким масштабом и подписи не читаются.
  const positions: Record<string, { x: number; y: number }> = {};
  let x = 0;
  for (const [, ids] of [...levels].sort(([a], [b]) => a - b)) {
    const cols = Math.ceil(ids.length / MAX_ROWS);
    const rows = Math.ceil(ids.length / cols);
    ids.forEach((id, i) => {
      const col = Math.floor(i / rows);
      const inCol = Math.min(rows, ids.length - col * rows);
      const stagger = col % 2 === 1 && inCol === rows ? ROW_GAP / 2 : 0;
      positions[id] = {
        x: x + col * SUB_COL_GAP,
        y: ((i % rows) - (inCol - 1) / 2) * ROW_GAP + stagger,
      };
    });
    x += (cols - 1) * SUB_COL_GAP + LEVEL_GAP;
  }
  return positions;
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
