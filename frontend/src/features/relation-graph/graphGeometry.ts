import type { GraphEdge } from '@/shared/api';
import { GRAPH_LABEL_WIDTH } from './graphAppearance';

export interface Point {
  x: number;
  y: number;
}

export interface CardBounds extends Point {
  width: number;
  height: number;
}

export interface EdgeRoute extends GraphEdge {
  id: string;
  path: string;
  labelPoint: Point | undefined;
  mask: CardBounds;
  lines: string[];
  labelWidth: number;
  labelHeight: number;
  emphasized: boolean;
}

function along(a: Point, b: Point, t: number): Point {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

function onCurve(a: Point, control: Point, b: Point, t: number): Point {
  return along(along(a, control, t), along(control, b, t), t);
}

function port(from: CardBounds, towards: Point): Point {
  const dx = towards.x - from.x;
  const dy = towards.y - from.y;
  const scale = Math.max(Math.abs(dx) / (from.width / 2), Math.abs(dy) / (from.height / 2));
  return scale ? { x: from.x + dx / scale, y: from.y + dy / scale } : from;
}

function intersects(a: CardBounds, b: CardBounds, gap: number) {
  return (
    Math.abs(a.x - b.x) < (a.width + b.width) / 2 + gap &&
    Math.abs(a.y - b.y) < (a.height + b.height) / 2 + gap
  );
}

function textLines(text: string, measure: (value: string) => number) {
  const words = text.trim().split(/\s+/);
  const lines: string[] = [];
  let line = '';
  for (const word of words) {
    const next = line ? line + ' ' + word : word;
    if (line && measure(next) > GRAPH_LABEL_WIDTH - 37) {
      lines.push(line);
      line = word;
    } else line = next;
  }
  if (line) lines.push(line);
  return lines;
}

export function routeGraphEdges(
  edges: (GraphEdge & { id: string; emphasized: boolean })[],
  cards: ReadonlyMap<string, CardBounds>,
  measure: (value: string) => number,
  reserveLabels: boolean,
): EdgeRoute[] {
  const occupied = [...cards.values()];
  const pairKey = (edge: GraphEdge) => [edge.source, edge.target].sort().join('|');
  const pairs = new Map<string, string[]>();
  for (const edge of edges) {
    const key = pairKey(edge);
    pairs.set(key, [...(pairs.get(key) ?? []), edge.id]);
  }

  return edges.flatMap((edge) => {
    const a = cards.get(edge.source);
    const b = cards.get(edge.target);
    if (!a || !b || a === b) return [];
    const center = along(a, b, 0.5);
    const length = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    const normal = { x: (a.y - b.y) / length, y: (b.x - a.x) / length };
    const parallel = pairs.get(pairKey(edge)) ?? [];
    const direction = edge.source < edge.target ? 1 : -1;
    const lane = (parallel.indexOf(edge.id) - (parallel.length - 1) / 2) * direction;
    const bend = lane * 148 || (edge.type === 'works_in' ? 12 : 35);
    const offsets = [bend, -bend, bend * 2, -bend * 2, bend * 3, -bend * 3, 0];
    const avoid =
      cards.size <= 36 ? [...cards.values()].filter((card) => card !== a && card !== b) : [];
    const geometry = offsets
      .map((offset) => {
        const control = { x: center.x + normal.x * offset, y: center.y + normal.y * offset };
        const start = port(a, control);
        const end = port(b, control);
        let obstructions = 0;
        for (let i = 1; avoid.length && i < 20; i++) {
          const point = onCurve(start, control, end, i / 20);
          if (avoid.some((card) => intersects(card, { ...point, width: 0, height: 0 }, 8)))
            obstructions++;
        }
        return { start, control, end, score: 400 * obstructions + Math.abs(offset - bend) };
      })
      .reduce((best, candidate) => (candidate.score < best.score ? candidate : best));
    const { start, control, end } = geometry;
    const pointAt = (t: number) => onCurve(start, control, end, t);
    const lines = textLines(edge.label, measure);
    const labelWidth = Math.min(GRAPH_LABEL_WIDTH, Math.max(48, ...lines.map(measure)) + 38);
    const labelHeight = lines.length * 14 + 10;
    let labelPoint: Point | undefined;

    if (lines.length && (edges.length <= 48 || edge.emphasized)) {
      for (const distance of [0, 18, -18, 33, -33, 52, -52, 75, -75]) {
        for (const t of [0.5, 0.38, 0.62, 0.28, 0.72, 0.18, 0.82]) {
          const point = pointAt(t);
          const candidate = {
            x: point.x + distance * normal.x,
            y: point.y + distance * normal.y,
            width: labelWidth,
            height: labelHeight,
          };
          if (!occupied.some((box) => intersects(box, candidate, 5))) {
            labelPoint = candidate;
            occupied.push(candidate);
            break;
          }
        }
        if (labelPoint) break;
      }
      if (!labelPoint && reserveLabels) labelPoint = pointAt(0.5);
    }

    const path = `M ${start.x} ${start.y} Q ${control.x} ${control.y} ${end.x} ${end.y}`;
    const minX = Math.min(start.x, end.x, control.x);
    const minY = Math.min(start.y, end.y, control.y);
    const mask = {
      x: minX - 12,
      y: minY - 12,
      width: Math.max(start.x, end.x, control.x) - minX + 24,
      height: Math.max(start.y, end.y, control.y) - minY + 24,
    };
    return [{ ...edge, path, lines, labelPoint, labelWidth, labelHeight, mask }];
  });
}
