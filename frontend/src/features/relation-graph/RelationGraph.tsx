import { ActionIcon, Alert, Button, Group, Select, Stack } from '@mantine/core';
import { IconMaximize, IconMinus, IconPlus } from '@tabler/icons-react';
import { useMediaQuery } from '@mantine/hooks';
import cytoscape, { type Core, type ElementDefinition, type EventObject } from 'cytoscape';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { GraphNode, OfficialGraph } from '@/shared/api';
import { graphHitAreas } from './graphStyle';
import { GraphVisual, type GraphView } from './GraphVisual';
import { compactPositions, evidenceEdge, graphElements, orbitPositions } from './graphModel';
import { GraphLegend } from './GraphLegend';

/** Самый крупный масштаб при вписывании: короткая цепочка (R07 из 3 узлов) не раздувается на весь экран. */
const MAX_FIT_ZOOM = 1.4;

/** Вписывает подсвеченную цепочку, а если её нет — весь граф. */
function fitGraph(cy: Core) {
  const focused = cy.elements('.hl');
  const target = focused.length ? focused : cy.elements();
  if (!target.length) return;
  cy.fit(target, Math.min(cy.width(), cy.height()) < 420 ? 20 : 35);
  if (cy.zoom() > MAX_FIT_ZOOM) {
    cy.zoom(MAX_FIT_ZOOM);
    cy.center(target);
  }
}

interface Props {
  graph: OfficialGraph;
  /** Узел, вокруг которого построен граф (крупнее остальных). */
  rootId?: string;
  rootSubtitle?: string;
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
  rootSubtitle,
  highlight,
  onNodeClick,
  selectedId,
  signalPicker,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const clickRef = useRef(onNodeClick);
  const wide = useMediaQuery('(min-width: 84em)');
  const narrow = useMediaQuery('(max-width: 37.99em)');
  const columns = narrow ? 1 : wide ? 3 : 2;
  const [layout, setLayout] = useState('breadthfirst');
  const [view, setView] = useState<GraphView>();
  const [hoveredId, setHoveredId] = useState<string>();
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
      style: graphHitAreas,
      layout:
        highlight?.length || (layout === 'breadthfirst' && graph.nodes.length <= 30)
          ? {
              name: 'preset',
              positions:
                !highlight?.length && !narrow && rootId && graph.nodes.length <= 14
                  ? orbitPositions(graph, rootId)
                  : compactPositions(graph, rootId, highlight, columns),
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
    cy.on('mouseover', 'node', (event) => setHoveredId(event.target.id()));
    cy.on('mouseout', 'node', () => setHoveredId(undefined));
    cyRef.current = cy;
    let frame = 0;
    let positionsDirty = true;
    let positions: GraphView['positions'] = {};
    const sync = (event?: EventObject) => {
      if (event?.type === 'position') positionsDirty = true;
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        if (positionsDirty) {
          positions = Object.fromEntries(cy.nodes().map((node) => [node.id(), node.position()]));
          positionsDirty = false;
        }
        setView({
          positions,
          pan: cy.pan(),
          zoom: cy.zoom(),
          width: cy.width(),
          height: cy.height(),
        });
      });
    };
    cy.on('position pan zoom', sync);
    const observer = new ResizeObserver(() => {
      cy.resize();
      fitGraph(cy);
      sync();
    });
    observer.observe(containerRef.current);
    sync();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements, layout, rootId, graph, highlight, columns, narrow]);

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
    fitGraph(cy);
  }, [highlight, elements, graph, layout, rootId, columns, narrow]);

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
      <div className="profile-graph-viewport">
        <div
          ref={containerRef}
          role="img"
          aria-label={`Граф связей: ${graph.nodes.length} узлов, ${graph.edges.length} связей`}
          data-testid="relation-graph"
          className="workspace-graph"
        />
        {view && (
          <GraphVisual
            key={highlight?.join('|') || 'all'}
            graph={graph}
            view={view}
            rootId={rootId}
            rootSubtitle={rootSubtitle}
            selectedId={selectedId}
            hoveredId={hoveredId}
            highlight={highlight}
            onNodeClick={onNodeClick}
          />
        )}
      </div>
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
            aria-label="Вписать граф"
            leftSection={<IconMaximize size={15} aria-hidden />}
            onClick={() => {
              if (cyRef.current) fitGraph(cyRef.current);
            }}
          >
            {view ? Math.round(view.zoom * 100) : 100}% · Центрировать
          </Button>
        </Group>
      </Group>
    </Stack>
  );
}
