import {
  Alert,
  Button,
  Group,
  Select,
  Stack,
  Switch,
  Text,
  useComputedColorScheme,
} from '@mantine/core';
import cytoscape, { type Core, type ElementDefinition } from 'cytoscape';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { GraphNode, OfficialGraph } from '@/shared/api';
import { buildStylesheet } from './graphStyle';
import { compactPositions, evidenceEdge, graphElements } from './graphModel';
import { groupContracts } from './contractGroups';
import { NODE_TYPE_LABELS } from '@/shared/lib/labels';

interface Props {
  graph: OfficialGraph;
  /** Узел, вокруг которого построен граф (крупнее остальных). */
  rootId?: string;
  /** id узлов, которые надо подсветить (например, evidence выбранного флага). */
  highlight?: string[];
  onNodeClick?: (node: GraphNode) => void;
  height?: number;
}

/** Тонкая обёртка над Cytoscape.js: создаёт инстанс на смену данных/темы, подсветку меняет классами. */
export function RelationGraph({ graph, rootId, highlight, onNodeClick, height = 520 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const clickRef = useRef(onNodeClick);
  const dark = useComputedColorScheme('light') === 'dark';
  const [layout, setLayout] = useState('breadthfirst');
  const [focused, setFocused] = useState<GraphNode | null>(null);
  const [grouped, setGrouped] = useState(true);
  const prepared = useMemo(
    () =>
      grouped ? groupContracts(graph, highlight) : { graph, aliases: new Map<string, string>() },
    [graph, grouped, highlight],
  );

  useEffect(() => {
    clickRef.current = onNodeClick;
  }, [onNodeClick]);

  const elements = useMemo<ElementDefinition[]>(
    () => graphElements(prepared.graph, rootId),
    [prepared, rootId],
  );

  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: buildStylesheet(dark),
      layout:
        layout === 'breadthfirst' && prepared.graph.nodes.length <= 30
          ? {
              name: 'preset',
              positions: compactPositions(
                prepared.graph,
                rootId,
                highlight?.map((id) => prepared.aliases.get(id) ?? id),
              ),
              fit: true,
              padding: 35,
            }
          : layout === 'breadthfirst'
            ? {
                name: 'breadthfirst',
                animate: false,
                padding: 45,
                roots: rootId ? [rootId] : undefined,
                directed: false,
                spacingFactor: 1.3,
                avoidOverlap: true,
                nodeDimensionsIncludeLabels: true,
              }
            : {
                name: 'cose',
                animate: false,
                padding: 45,
                nodeRepulsion: () => 9000,
                idealEdgeLength: () => 110,
                nodeDimensionsIncludeLabels: true,
              },
      minZoom: 0.05,
      maxZoom: 2.5,
      wheelSensitivity: 0.3,
    });
    cy.on('tap', 'node', (evt) => {
      const node = evt.target.data() as GraphNode;
      setFocused(node);
      clickRef.current?.(node);
    });
    cy.on('mouseover', 'node', (evt) => setFocused(evt.target.data() as GraphNode));
    cyRef.current = cy;
    const observer = new ResizeObserver(() => {
      cy.resize();
      cy.fit(cy.elements('.hl').length ? cy.elements('.hl') : undefined, 45);
    });
    observer.observe(containerRef.current);
    return () => {
      observer.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements, dark, layout, rootId, prepared, highlight]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass('faded hl');
      if (!highlight?.length) return;
      const ids = new Set(highlight.map((id) => prepared.aliases.get(id) ?? id));
      cy.elements().addClass('faded');
      cy.nodes()
        .filter((n) => ids.has(n.id()))
        .removeClass('faded')
        .addClass('hl');
      cy.edges()
        .filter((e) => evidenceEdge(e.data(), ids, prepared.graph))
        .removeClass('faded')
        .addClass('hl');
    });
    cy.fit(highlight?.length ? cy.elements('.hl') : undefined, 45);
  }, [highlight, elements, dark, prepared, layout]);

  return (
    <Stack gap="xs">
      <Group justify="space-between">
        <Select
          aria-label="Раскладка графа"
          value={layout}
          onChange={(value) => value && setLayout(value)}
          allowDeselect={false}
          data={[
            { value: 'breadthfirst', label: 'По уровням' },
            { value: 'cose', label: 'Силовая' },
          ]}
          w={170}
        />
        <Button
          variant="subtle"
          size="xs"
          onClick={() => {
            const cy = cyRef.current;
            if (cy) cy.fit(cy.elements('.hl').length ? cy.elements('.hl') : undefined, 45);
          }}
        >
          Вписать граф
        </Button>
      </Group>
      <Switch
        label="Группировать контракты одного поставщика и заказчика"
        checked={grouped}
        onChange={(e) => setGrouped(e.currentTarget.checked)}
        size="xs"
      />
      {graph.nodes.length === 0 && <Alert>Связи не найдены</Alert>}
      {graph.truncated && (
        <Alert color="orange">Показана часть связей: сервер ограничил размер графа.</Alert>
      )}
      <div
        ref={containerRef}
        role="img"
        aria-label={`Граф связей: ${graph.nodes.length} узлов, ${graph.edges.length} связей`}
        data-testid="relation-graph"
        style={{
          height,
          width: '100%',
          borderRadius: 'var(--mantine-radius-md)',
          border: '1px solid var(--mantine-color-default-border)',
        }}
      />
      <Text size="xs" c="dimmed" mih={32} role="status">
        {focused && prepared.graph.nodes.some((n) => n.id === focused.id)
          ? `${NODE_TYPE_LABELS[focused.type]}: ${focused.label}${focused.risk != null ? ` · риск ${focused.risk}/100` : ''}`
          : 'Наведите указатель на узел, чтобы увидеть полную подпись.'}
      </Text>
    </Stack>
  );
}
