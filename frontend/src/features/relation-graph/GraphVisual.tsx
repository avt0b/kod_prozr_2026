import { useEffect, useId, useMemo, useState, type CSSProperties } from 'react';
import type { GraphEdge, GraphNode, OfficialGraph } from '@/shared/api';
import { NODE_TYPE_LABELS } from '@/shared/lib/labels';
import {
  GRAPH_APPEARANCE,
  GRAPH_CARD_HEIGHT,
  GRAPH_CARD_WIDTH,
  GRAPH_ROOT_HEIGHT,
  GRAPH_ROOT_WIDTH,
} from './graphAppearance';
import { routeGraphEdges, type CardBounds, type EdgeRoute, type Point } from './graphGeometry';
import { cardLabel, evidenceEdge } from './graphModel';
import './graphVisual.css';

const tones = {
  manual: 'blue',
  kinship: 'red',
  works_in: 'green',
  founder: 'amber',
  director: 'amber',
  employment: 'amber',
  supplier: 'violet',
  customer: 'violet',
  mentions: 'teal',
  shared_contact: 'red',
} as const;

export interface GraphView {
  positions: Record<string, Point>;
  pan: Point;
  zoom: number;
  width: number;
  height: number;
}

interface Props {
  graph: OfficialGraph;
  view: GraphView;
  rootId?: string;
  rootSubtitle?: string;
  selectedId?: string;
  hoveredId?: string;
  highlight?: string[];
  onNodeClick?: (node: GraphNode) => void;
}

function tone(edge: GraphEdge) {
  return edge.type === 'kinship' && edge.label.startsWith('супруг') ? 'blue' : tones[edge.type];
}

function relationLabel(label: string): string {
  const names: Record<string, string> = {
    'супруг(а)': 'Супруг / супруга',
    'брат/сестра': 'Брат / сестра',
  };
  return names[label] ?? label;
}

function GraphStroke({
  route,
  index,
  mask,
  animate,
  muted,
  selected,
}: {
  route: EdgeRoute;
  index: number;
  mask: string;
  animate: boolean;
  muted?: boolean;
  selected: boolean;
}) {
  return (
    <g
      className="graph-link"
      data-tone={tone(route)}
      data-highlighted={route.emphasized || undefined}
      data-selected={selected || undefined}
      data-muted={muted || undefined}
      data-solid={route.type === 'works_in' || undefined}
      style={{ '--graph-order': Math.min(index, 9) } as CSSProperties}
    >
      {animate && !muted && (
        <mask id={mask} maskUnits="userSpaceOnUse" {...route.mask}>
          <path
            className="graph-stroke-reveal"
            d={route.path}
            pathLength={1}
            stroke="white"
            strokeWidth={12}
            fill="none"
          />
        </mask>
      )}
      <path
        className="graph-link-track"
        d={route.path}
        mask={animate && !muted ? `url(#${mask})` : undefined}
      />
      {(route.emphasized || selected) && (
        <path className="graph-link-flow" d={route.path} pathLength={1} />
      )}
    </g>
  );
}

export function GraphVisual({
  graph,
  view,
  rootId,
  rootSubtitle,
  selectedId,
  hoveredId,
  highlight,
  onNodeClick,
}: Props) {
  const instance = useId().replaceAll(':', '');
  const [replay, setReplay] = useState(0);
  useEffect(() => {
    const restart = () => setReplay((value) => value + 1);
    document.addEventListener('workspace:replay-motion', restart);
    return () => document.removeEventListener('workspace:replay-motion', restart);
  }, []);

  const { positions, pan, zoom, width, height } = view;
  const { cards, active, muted, relationships } = useMemo(() => {
    const focus = new Set(highlight);
    const geometry = new Map<string, CardBounds>();
    for (const node of graph.nodes) {
      const pos = positions[node.id];
      if (!pos) continue;
      const isRoot = node.id === rootId;
      geometry.set(node.id, {
        ...pos,
        width: isRoot ? GRAPH_ROOT_WIDTH : GRAPH_CARD_WIDTH,
        height: isRoot ? GRAPH_ROOT_HEIGHT : GRAPH_CARD_HEIGHT,
      });
    }
    const relationships = new Map(
      graph.edges.filter((edge) => edge.source === rootId).map((edge) => [edge.target, edge]),
    );
    const all = graph.edges.map((edge, i) => ({
      ...edge,
      id: `edge:${i}:${edge.source}:${edge.target}`,
      emphasized: focus.size > 0 && evidenceEdge(edge, focus, graph),
    }));
    const labelContext = document.createElement('canvas').getContext('2d');
    if (labelContext) labelContext.font = '600 12px system-ui, sans-serif';
    const measure = (value: string) => labelContext?.measureText(value).width ?? value.length * 6.5;
    const front = focus.size ? new Map([...geometry].filter(([id]) => focus.has(id))) : geometry;
    return {
      cards: geometry,
      relationships,
      active: routeGraphEdges(
        focus.size ? all.filter((edge) => edge.emphasized) : all,
        front,
        measure,
        focus.size > 0,
      ),
      muted: focus.size
        ? routeGraphEdges(
            all.filter((edge) => !edge.emphasized),
            geometry,
            measure,
            false,
          )
        : [],
    };
  }, [graph, positions, rootId, highlight]);

  const lead =
    selectedId === rootId && !highlight?.length
      ? active.find(
          (edge) =>
            edge.source === rootId &&
            edge.type === 'kinship' &&
            graph.edges.some((link) => link.source === edge.target && link.type === 'founder'),
        )?.id
      : undefined;
  const isSelectedLine = (edge: EdgeRoute) =>
    edge.id === lead ||
    (selectedId !== rootId && (edge.source === selectedId || edge.target === selectedId));

  return (
    <div className="graph-visual">
      <div
        className="graph-world"
        key={replay}
        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
      >
        <svg className="graph-link-layer" width={1} height={1} aria-hidden="true">
          {muted.map((route, index) => (
            <GraphStroke
              key={route.id}
              route={route}
              index={index}
              mask=""
              animate={false}
              muted
              selected={false}
            />
          ))}
          {active.map((route, index) => (
            <GraphStroke
              key={route.id}
              route={route}
              index={index}
              mask={`${instance}-line-${index}`}
              animate={active.length <= 40}
              selected={isSelectedLine(route)}
            />
          ))}
        </svg>
        {active.map(
          (route, index) =>
            route.labelPoint && (
              <div
                className="graph-edge-pill"
                key={route.id}
                data-graph-edge-label={route.id}
                data-highlighted={route.emphasized || undefined}
                data-tone={tone(route)}
                style={
                  {
                    left: route.labelPoint.x,
                    top: route.labelPoint.y,
                    width: route.labelWidth,
                    minHeight: route.labelHeight,
                    '--graph-order': Math.min(index, 9),
                  } as CSSProperties
                }
              >
                <i aria-hidden="true" />
                <span>
                  {route.type === 'manual' ? '✎ ' : ''}
                  {route.lines.join('\n')}
                </span>
              </div>
            ),
        )}
        {graph.nodes.map((node, index) => {
          const box = cards.get(node.id);
          if (!box) return null;
          const isRoot = node.id === rootId;
          const related = relationships.get(node.id);
          const subdued = Boolean(highlight?.length && !highlight.includes(node.id));
          const selected = node.id === selectedId;
          const relationship = related?.type === 'kinship' ? relationLabel(related.label) : '';
          const caption = isRoot
            ? 'Служащий · Фокус'
            : relationship ||
              (related?.type === 'employment'
                ? 'Бывший работодатель'
                : NODE_TYPE_LABELS[node.type]);
          const subtitle = isRoot ? rootSubtitle : undefined;
          const Icon = GRAPH_APPEARANCE[node.type];
          const rx = box.x * zoom + pan.x;
          const ry = box.y * zoom + pan.y;
          const visible = rx >= 0 && ry >= 0 && rx <= width && ry <= height;
          return (
            <button
              type="button"
              className="graph-card"
              key={node.id}
              data-graph-card={node.id}
              data-manual={node.manual || undefined}
              data-type={node.type}
              data-root={isRoot || undefined}
              data-kin={relationship && !relationship.startsWith('Супруг') ? true : undefined}
              data-focused={selected || undefined}
              data-hovered={node.id === hoveredId || undefined}
              data-highlighted={Boolean(highlight?.includes(node.id)) || undefined}
              data-muted={subdued || undefined}
              tabIndex={!subdued && visible ? 0 : -1}
              aria-label={node.label.replaceAll('\n', ' ')}
              aria-pressed={selected}
              onClick={() => onNodeClick?.(node)}
              style={
                {
                  left: box.x,
                  top: box.y,
                  width: box.width,
                  height: box.height,
                  '--graph-order': Math.min(index, 9),
                } as CSSProperties
              }
            >
              <span className="graph-card-face">
                <span className="graph-card-icon" aria-hidden="true">
                  <svg width={23} height={23} viewBox="0 0 24 24" fill="none">
                    <path
                      d={Icon.path}
                      stroke="currentColor"
                      strokeWidth={1.65}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                <span className="graph-card-copy">
                  <span className="graph-card-meta">
                    <span className="graph-card-type">
                      {node.manual ? 'Внесено аналитиком' : caption}
                    </span>
                    {isRoot && node.risk != null && (
                      <span className="graph-card-risk">Риск {node.risk}</span>
                    )}
                  </span>
                  <strong className="graph-card-name">{cardLabel(node)}</strong>
                  {subtitle && <span className="graph-card-description">{subtitle}</span>}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
