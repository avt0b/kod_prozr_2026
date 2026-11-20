import type { GraphEdge, GraphNode, OfficialGraph } from '@/shared/api';
import { GRAPH_LABEL_WIDTH, GRAPH_ROOT_WIDTH } from './graphAppearance.ts';

/** Шаг раскладки «по уровням», px: между уровнями, между колонками одного уровня, между строками. */
const LEVEL_GAP = 278;
const SUB_COL_GAP = 228;
const ROW_GAP = 112;
// Leave room for the entire horizontal label between the two widest cards.
const CHAIN_GAP = GRAPH_ROOT_WIDTH + GRAPH_LABEL_WIDTH + 32;
const CHAIN_ROW_GAP = 124;
const MAX_ROWS = 5;

/** Раскладывает простую цепочку строками и оставляет прежнюю раскладку для ветвлений. */
function chainPositions(graph: OfficialGraph, rootId: string | undefined, columns: number) {
  const neighbours = new Map(graph.nodes.map((node) => [node.id, new Set<string>()]));
  for (const edge of graph.edges) {
    neighbours.get(edge.source)?.add(edge.target);
    neighbours.get(edge.target)?.add(edge.source);
  }
  const ends = [...neighbours].filter(([, ids]) => ids.size === 1).map(([id]) => id);
  if (ends.length !== 2 || [...neighbours.values()].some((ids) => ids.size > 2)) return null;
  const start = rootId && ends.includes(rootId) ? rootId : ends[0];
  const order = [start];
  for (let i = 0; i < order.length; i++) {
    const next = [...(neighbours.get(order[i]) ?? [])].find((id) => !order.includes(id));
    if (next) order.push(next);
  }
  const isolated = [...neighbours].filter(([, ids]) => ids.size === 0).map(([id]) => id);
  if (order.length + isolated.length !== neighbours.size) return null;
  order.push(...isolated);

  const rowPositions = [0];
  for (let index = columns; index < order.length; index += columns) {
    const previous = order[index - 1];
    const next = order[index];
    const parallel = graph.edges.filter(
      (edge) =>
        (edge.source === previous && edge.target === next) ||
        (edge.source === next && edge.target === previous),
    ).length;
    rowPositions.push(rowPositions.at(-1)! + CHAIN_ROW_GAP + Math.max(0, parallel - 1) * 32);
  }

  return Object.fromEntries(
    order.map((id, index) => {
      const row = Math.floor(index / columns);
      const column = index % columns;
      return [
        id,
        { x: (row % 2 ? columns - 1 - column : column) * CHAIN_GAP, y: rowPositions[row] },
      ];
    }),
  );
}

/** Horizontal levels keep H1's wide first neighbourhood readable on a laptop. */
export function compactPositions(
  graph: OfficialGraph,
  rootId?: string,
  highlight: string[] = [],
  chainColumns = 3,
): Record<string, { x: number; y: number }> {
  if (highlight.length) {
    const ids = new Set(highlight);
    const evidence = {
      ...graph,
      nodes: graph.nodes.filter((node) => ids.has(node.id)),
      edges: graph.edges.filter((edge) => evidenceEdge(edge, ids, graph)),
    };
    if (evidence.nodes.length) {
      const focused =
        chainPositions(evidence, rootId, chainColumns) ??
        levelPositions(evidence, rootId, CHAIN_GAP, CHAIN_ROW_GAP);
      const other = {
        ...graph,
        nodes: graph.nodes.filter((node) => !ids.has(node.id)),
        edges: graph.edges.filter((edge) => !ids.has(edge.source) && !ids.has(edge.target)),
      };
      const visibleEnd = Math.max(...Object.values(focused).map(({ x }) => x));
      return {
        ...Object.fromEntries(
          Object.entries(levelPositions(other)).map(([id, position]) => [
            id,
            { x: position.x + visibleEnd + CHAIN_GAP, y: position.y },
          ]),
        ),
        ...focused,
      };
    }
  }
  return levelPositions(graph, rootId);
}

function levelPositions(
  graph: OfficialGraph,
  rootId?: string,
  levelGap = LEVEL_GAP,
  rowGap = ROW_GAP,
): Record<string, { x: number; y: number }> {
  const root = graph.nodes.find((node) => node.id === rootId)?.id ?? graph.nodes[0]?.id;
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
      const stagger = col % 2 === 1 && inCol === rows ? rowGap / 2 : 0;
      positions[id] = {
        x: x + col * SUB_COL_GAP,
        y: ((i % rows) - (inCol - 1) / 2) * rowGap + stagger,
      };
    });
    x += (cols - 1) * SUB_COL_GAP + levelGap;
  }
  return positions;
}

/** Evidence describes a subgraph; the employment shortcut is outside an R01 chain. */
export function evidenceEdge(edge: GraphEdge, ids: Set<string>, graph: OfficialGraph): boolean {
  if (!ids.has(edge.source) || !ids.has(edge.target)) return false;
  const hasContracts = graph.nodes.some((n) => n.type === 'contract' && ids.has(n.id));
  return !(hasContracts && ['works_in', 'appointment'].includes(edge.type));
}

function cardLabel(node: GraphNode): string {
  if (node.type === 'person') {
    const [surname, ...names] = node.label.trim().split(/\s+/);
    return [surname, ...names.map((name) => `${name[0]}.`)].join(' ');
  }
  const label =
    node.type === 'company' ? node.label.replace(/^(?:ООО|АО|ПАО)\s+«(.+)»$/, '$1') : node.label;
  const limit = node.type === 'organ' ? 27 : 42;
  const characters = Array.from(label);
  return characters.length > limit
    ? `${characters
        .slice(0, limit - 1)
        .join('')
        .trimEnd()}…`
    : label;
}

export function graphElements(graph: OfficialGraph, rootId?: string) {
  const ids = new Set(graph.nodes.map((n) => n.id));
  return [
    ...graph.nodes.map((node) => ({
      data: { ...node, cardLabel: cardLabel(node), risk: node.risk ?? undefined },
      classes: node.id === rootId ? 'root' : undefined,
    })),
    ...graph.edges
      .filter((e) => ids.has(e.source) && ids.has(e.target))
      .map((edge, i) => ({
        data: { ...edge, id: `edge:${i}:${edge.source}:${edge.target}` },
      })),
  ];
}
