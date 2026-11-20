import {
  ActionIcon,
  Alert,
  Button,
  Group,
  Select,
  Stack,
  Text,
  useComputedColorScheme,
} from '@mantine/core';
import { IconMaximize, IconMinus, IconPlus } from '@tabler/icons-react';
import { useMediaQuery, useReducedMotion } from '@mantine/hooks';
import cytoscape, { type Core, type ElementDefinition } from 'cytoscape';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { GraphNode, OfficialGraph } from '@/shared/api';
import { buildStylesheet } from './graphStyle';
import { compactPositions, evidenceEdge, graphElements } from './graphModel';
import { GraphLegend } from './GraphLegend';

/** Самый крупный масштаб при вписывании: короткая цепочка (R07 из 3 узлов) не раздувается на весь экран. */
const MAX_FIT_ZOOM = 1.4;

/** Вписывает подсвеченную цепочку, а если её нет — весь граф. */
function fitGraph(cy: Core) {
  const target = cy.elements('.hl').length ? cy.elements('.hl') : cy.elements();
  if (!target.length) return;
  cy.fit(target, Math.min(cy.width(), cy.height()) < 420 ? 20 : 35);
  if (cy.zoom() > MAX_FIT_ZOOM) {
    cy.zoom(MAX_FIT_ZOOM);
    cy.center(target);
  }
}

// Canvas labels stay pinned to their edge's midpoint, with a small offset when cards
// or another label occupy that spot. Two edges between the same nodes get separate slots.
function placeEdgeLabels(cy: Core) {
  const highlighted = cy.elements('.hl');
  const edges = highlighted.length ? highlighted.edges() : cy.edges();
  if (edges.length > 60) return;
  const nodes = highlighted.length ? highlighted.nodes() : cy.nodes();
  const occupied = nodes.map((node) => node.boundingBox({ includeLabels: false }));
  const parallel = new Map<string, string[]>();
  const groupKey = (source: string, target: string) => JSON.stringify([source, target].sort());
  edges.forEach((edge) => {
    const key = groupKey(edge.source().id(), edge.target().id());
    parallel.set(key, [...(parallel.get(key) ?? []), edge.id()]);
  });
  edges.removeStyle('label text-margin-x text-margin-y');
  edges.forEach((edge) => {
    const box = edge.boundingBox({
      includeNodes: false,
      includeEdges: false,
      includeOverlays: false,
      includeLabels: true,
    });
    if (!box.w || !box.h) return;
    const pair = parallel.get(groupKey(edge.source().id(), edge.target().id())) ?? [];
    const offset = (pair.indexOf(edge.id()) - (pair.length - 1) / 2) * 42;
    const candidates = [
      [0, offset],
      [0, 0],
      [0, 20],
      [0, -20],
      [24, 0],
      [-24, 0],
      [0, 36],
      [0, -36],
      [36, 18],
      [-36, 18],
      [36, -18],
      [-36, -18],
    ];
    for (const [x, y] of candidates) {
      const label = { x1: box.x1 + x, x2: box.x2 + x, y1: box.y1 + y, y2: box.y2 + y };
      if (
        occupied.some(
          (b) =>
            b.x1 < label.x2 + 2 &&
            label.x1 - 2 < b.x2 &&
            b.y1 < label.y2 + 2 &&
            label.y1 - 2 < b.y2,
        )
      )
        continue;
      edge.style({ 'text-margin-x': `${x}px`, 'text-margin-y': `${y}px` });
      occupied.push({ ...label, w: box.w, h: box.h });
      return;
    }
    if (!highlighted.length) edge.style('label', '');
  });
}

interface Props {
  graph: OfficialGraph;
  /** Узел, вокруг которого построен граф (крупнее остальных). */
  rootId?: string;
  /** id узлов, которые надо подсветить (например, evidence выбранного флага). */
  highlight?: string[];
  onNodeClick?: (node: GraphNode) => void;
  selectedId?: string;
  signalPicker?: ReactNode;
}

/** Тонкая обёртка над Cytoscape.js: создаёт инстанс на смену данных/темы, подсветку меняет классами. */
export function RelationGraph({
  graph,
  rootId,
  highlight,
  onNodeClick,
  selectedId,
  signalPicker,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const clickRef = useRef(onNodeClick);
  const dark = useComputedColorScheme('light') === 'dark';
  const reducedMotion = useReducedMotion();
  const wide = useMediaQuery('(min-width: 84em)');
  const narrow = useMediaQuery('(max-width: 37.99em)');
  const columns = narrow ? 1 : wide ? 3 : 2;
  const [layout, setLayout] = useState('breadthfirst');
  const [zoomPercent, setZoomPercent] = useState(100);
  useEffect(() => {
    clickRef.current = onNodeClick;
  }, [onNodeClick]);

  const elements = useMemo<ElementDefinition[]>(
    () => graphElements(graph, rootId),
    [graph, rootId],
  );

  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: buildStylesheet(dark),
      layout:
        highlight?.length || (layout === 'breadthfirst' && graph.nodes.length <= 30)
          ? {
              name: 'preset',
              positions: compactPositions(graph, rootId, highlight, columns),
              fit: false,
            }
          : layout === 'breadthfirst'
            ? {
                name: 'breadthfirst',
                animate: false,
                padding: 45,
                roots: rootId ? [rootId] : undefined,
                directed: false,
                spacingFactor: 1.45,
                avoidOverlap: true,
                nodeDimensionsIncludeLabels: true,
              }
            : {
                name: 'cose',
                animate: false,
                padding: 45,
                nodeRepulsion: () => 17000,
                idealEdgeLength: () => 220,
                nodeDimensionsIncludeLabels: true,
              },
      minZoom: 0.05,
      maxZoom: 2.5,
    });
    cy.on('tap', 'node', (evt) => {
      const node = evt.target.data() as GraphNode;
      clickRef.current?.(node);
    });
    cy.on('zoom', () => setZoomPercent(Math.round(cy.zoom() * 100)));
    cy.on('dragfree', 'node', () => placeEdgeLabels(cy));
    cyRef.current = cy;
    const observer = new ResizeObserver(() => {
      cy.resize();
      fitGraph(cy);
    });
    observer.observe(containerRef.current);
    return () => {
      observer.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements, dark, layout, rootId, graph, highlight, columns]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass('faded hl');
      if (!highlight?.length) return;
      const ids = new Set(highlight);
      cy.elements().addClass('faded');
      cy.nodes()
        .filter((n) => ids.has(n.id()))
        .removeClass('faded')
        .addClass('hl');
      cy.edges()
        .filter((e) => evidenceEdge(e.data(), ids, graph))
        .removeClass('faded')
        .addClass('hl');
    });
    placeEdgeLabels(cy);
    fitGraph(cy);
    if (reducedMotion) return;
    let animation: Animation | undefined;
    const reveal = () => {
      animation?.cancel();
      animation = containerRef.current?.animate(
        [
          { opacity: 0.35, transform: 'translateY(5px)' },
          { opacity: 1, transform: 'translateY(0)' },
        ],
        {
          duration: highlight?.length ? 260 : 380,
          easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
        },
      );
    };
    const syncVisibility = () => {
      if (document.hidden && animation?.playState === 'running') animation.pause();
      else if (!document.hidden && animation?.playState === 'paused') animation.play();
    };
    reveal();
    syncVisibility();
    document.addEventListener('workspace:replay-motion', reveal);
    document.addEventListener('visibilitychange', syncVisibility);
    return () => {
      animation?.cancel();
      document.removeEventListener('workspace:replay-motion', reveal);
      document.removeEventListener('visibilitychange', syncVisibility);
    };
  }, [highlight, elements, dark, graph, layout, reducedMotion, rootId, columns]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.nodes('.active-node').removeClass('active-node');
      if (selectedId) cy.getElementById(selectedId).addClass('active-node');
    });
  }, [selectedId, elements, dark, layout, graph, highlight, rootId, columns]);

  const changeZoom = (factor: number) => {
    const cy = cyRef.current;
    if (cy) {
      cy.zoom({
        level: cy.zoom() * factor,
        renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
      });
    }
  };

  return (
    <Stack
      className="profile-graph-content"
      gap="xs"
      data-focused={Boolean(highlight?.length) || undefined}
    >
      <Group className="profile-graph-toolbar" gap="xs">
        {signalPicker}
        {!highlight?.length && (
          <Select
            aria-label="Раскладка графа"
            value={layout}
            onChange={(value) => value && setLayout(value)}
            allowDeselect={false}
            data={[
              { value: 'breadthfirst', label: 'По уровням' },
              { value: 'cose', label: 'Силовая' },
            ]}
            className="profile-graph-layout"
            size="xs"
          />
        )}
      </Group>
      {graph.nodes.length === 0 && <Alert>Связи не найдены</Alert>}
      {graph.truncated && (
        <Alert color="orange">Показана часть связей: сервер ограничил размер графа.</Alert>
      )}
      <div
        ref={containerRef}
        role="img"
        aria-label={`Граф связей: ${graph.nodes.length} узлов, ${graph.edges.length} связей`}
        data-testid="relation-graph"
        className="workspace-graph"
      />
      <Group className="profile-graph-dock" justify="space-between" gap="xs">
        <div className="profile-graph-key profile-glass">
          <GraphLegend />
        </div>
        <Group className="profile-graph-zoom profile-glass" gap={4} wrap="nowrap">
          <ActionIcon
            variant="subtle"
            color="gray"
            size={38}
            aria-label="Отдалить граф"
            onClick={() => changeZoom(1 / 1.2)}
          >
            <IconMinus size={17} aria-hidden />
          </ActionIcon>
          <Text size="xs" fw={650} aria-label="Масштаб графа">
            {zoomPercent}%
          </Text>
          <ActionIcon
            variant="subtle"
            color="gray"
            size={38}
            aria-label="Приблизить граф"
            onClick={() => changeZoom(1.2)}
          >
            <IconPlus size={17} aria-hidden />
          </ActionIcon>
          <Button
            className="profile-graph-fit"
            variant="subtle"
            color="gray"
            size="xs"
            leftSection={<IconMaximize size={15} aria-hidden />}
            onClick={() => {
              if (cyRef.current) fitGraph(cyRef.current);
            }}
          >
            Вписать граф
          </Button>
        </Group>
      </Group>
    </Stack>
  );
}
