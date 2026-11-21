import type { GraphEdge, GraphNode, OfficialGraph } from '@/shared/api';
import { GRAPH_CARD_WIDTH, GRAPH_LABEL_WIDTH, GRAPH_ROOT_WIDTH } from './graphAppearance.ts';

/** Шаг раскладки «по уровням», px: между уровнями, между колонками одного уровня, между строками. */
const LEVEL_GAP = 278;
const SUB_COL_GAP = GRAPH_CARD_WIDTH + 28;
const ROW_GAP = 112;
// Leave room for the entire horizontal label between the two widest cards.
const CHAIN_GAP = GRAPH_ROOT_WIDTH + GRAPH_LABEL_WIDTH + 32;
const CHAIN_ROW_GAP = 144;
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

/** A small case spreads around the selected official like the reference canvas. */
export function orbitPositions(graph: OfficialGraph, rootId: string) {
  const result: Record<string, { x: number; y: number }> = { [rootId]: { x: 0, y: 0 } };
  const outgoing = (id: string) => graph.edges.filter((edge) => edge.source === id);
  const rootEdges = outgoing(rootId);
  const place = (id: string | undefined, x: number, y: number) => {
    if (id && !result[id]) result[id] = { x: x * 0.84, y };
  };
  const organ = rootEdges.find((edge) => edge.type === 'works_in')?.target;
  const former = rootEdges.find((edge) => edge.type === 'employment')?.target;
  const relatives = rootEdges.filter((edge) => edge.type === 'kinship');
  const linkedRelative = relatives.find((edge) =>
    outgoing(edge.target).some((link) => link.type === 'founder' || link.type === 'director'),
  )?.target;
  const supplier =
    linkedRelative &&
    outgoing(linkedRelative).find((edge) => edge.type === 'founder' || edge.type === 'director')
      ?.target;
  const spouse = relatives.find((edge) => edge.label.startsWith('супруг'))?.target;
  const appeal = graph.edges.find(
    (edge) => edge.type === 'mentions' && edge.target === rootId,
  )?.source;
  place(organ, 62, -255);
  place(linkedRelative, -303, -262);
  place(spouse, 407, -207);
  place(supplier, -557, -28);
  place(former, 441, 58);
  place(supplier && outgoing(supplier).find((edge) => edge.type === 'supplier')?.target, -503, 206);
  place(former && outgoing(former).find((edge) => edge.type === 'supplier')?.target, 514, 254);
  place(appeal, -79, 291);
  const vacant = [
    [388, -333],
    [-598, -178],
    [-344, 325],
    [242, 297],
    [0, 426],
    [686, -52],
    [-810, -99],
    [722, 372],
    [710, -304],
    [-775, 315],
    [443, 476],
  ];
  graph.nodes
    .filter((node) => !result[node.id])
    .forEach((node, index) => {
      const [x, y] = vacant[index] ?? [650, index * ROW_GAP];
      place(node.id, x, y);
    });
  return result;
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

/** Two columns use the height of a phone instead of compressing a horizontal graph. */
export function mobilePositions(
  graph: OfficialGraph,
  rootId?: string,
): Record<string, { x: number; y: number }> {
  const levels = levelPositions(graph, rootId);
  const nodes = [...graph.nodes].sort((a, b) =>
    a.id === rootId ? -1 : b.id === rootId ? 1 : (levels[a.id]?.x ?? 0) - (levels[b.id]?.x ?? 0),
  );
  return Object.fromEntries(
    nodes.map((node, index) => [
      node.id,
      {
        x: (index % 2) * (GRAPH_ROOT_WIDTH + 36),
        y: Math.floor(index / 2) * 118,
      },
    ]),
  );
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

export function cardLabel(node: GraphNode): string {
  if (node.type === 'person') {
    const [surname, ...names] = node.label.trim().split(/\s+/);
    return [surname, ...names.map((name) => `${name[0]}.`)].join(' ');
  }
  const label = node.label;
  const limit = node.type === 'organ' ? 41 : 51;
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
