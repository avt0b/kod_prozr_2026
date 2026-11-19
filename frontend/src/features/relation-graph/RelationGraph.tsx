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
import { IconMaximize } from '@tabler/icons-react';
import { useMediaQuery, useReducedMotion } from '@mantine/hooks';
import cytoscape, { type Core, type ElementDefinition } from 'cytoscape';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { GraphNode, OfficialGraph } from '@/shared/api';
import { buildStylesheet } from './graphStyle';
import { compactPositions, evidenceEdge, graphElements } from './graphModel';
import { groupContracts } from './contractGroups';
import { NODE_TYPE_LABELS } from '@/shared/lib/labels';

/** Самый крупный масштаб при вписывании: короткая цепочка (R07 из 3 узлов) не раздувается на весь экран. */
const MAX_FIT_ZOOM = 1.4;

/** Вписывает подсвеченную цепочку, а если её нет — весь граф. */
function fitGraph(cy: Core) {
  const target = cy.elements('.hl').length ? cy.elements('.hl') : cy.elements();
  cy.fit(target, Math.min(cy.width(), cy.height()) < 400 ? 20 : 45);
  if (cy.zoom() > MAX_FIT_ZOOM) {
    cy.zoom(MAX_FIT_ZOOM);
    cy.center(target);
  }
}

interface Props {
  graph: OfficialGraph;
  /** Узел, вокруг которого построен граф (крупнее остальных). */
  rootId?: string;
  /** id узлов, которые надо подсветить (например, evidence выбранного флага). */
  highlight?: string[];
  onNodeClick?: (node: GraphNode) => void;
  signalPicker?: ReactNode;
}

/** Тонкая обёртка над Cytoscape.js: создаёт инстанс на смену данных/темы, подсветку меняет классами. */
export function RelationGraph({ graph, rootId, highlight, onNodeClick, signalPicker }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const clickRef = useRef(onNodeClick);
  const dark = useComputedColorScheme('light') === 'dark';
  const reducedMotion = useReducedMotion();
  const mobile = useMediaQuery('(max-width: 47.99em)');
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
                mobile ? 2 : 3,
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
      fitGraph(cy);
    });
    observer.observe(containerRef.current);
    return () => {
      observer.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements, dark, layout, rootId, prepared, highlight, mobile]);

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
    fitGraph(cy);
    if (reducedMotion) return;
    let animation: Animation | undefined;
    const reveal = () => {
      animation?.cancel();
      animation = containerRef.current?.animate(
        [
          { opacity: 0.4, filter: 'blur(3px)', clipPath: 'inset(4% 0 4% 0 round 16px)' },
          { opacity: 1, filter: 'blur(0px)', clipPath: 'inset(0% 0 0% 0 round 16px)' },
        ],
        {
          duration: highlight?.length ? 420 : 650,
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
  }, [highlight, elements, dark, prepared, layout, reducedMotion]);

  return (
    <Stack gap="xs">
      <Group className="profile-graph-toolbar" gap="xs">
        {signalPicker}
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
        <Switch
          label="Группировать"
          aria-label="Группировать контракты одного поставщика и заказчика"
          checked={grouped}
          onChange={(e) => setGrouped(e.currentTarget.checked)}
          size="xs"
        />
        <Button
          className="profile-graph-fit"
          variant="default"
          size="xs"
          leftSection={<IconMaximize size={14} aria-hidden />}
          onClick={() => {
            const cy = cyRef.current;
            if (cy) fitGraph(cy);
          }}
        >
          Вписать граф
        </Button>
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
      <Text className="profile-graph-status" size="xs" c="dimmed" role="status">
        {focused && prepared.graph.nodes.some((n) => n.id === focused.id)
          ? `${NODE_TYPE_LABELS[focused.type]}: ${focused.label}${focused.risk != null ? ` · риск ${focused.risk}/100` : ''}`
          : 'Наведите на узел для полной подписи. Профили и обращения открываются по нажатию.'}
      </Text>
    </Stack>
  );
}
