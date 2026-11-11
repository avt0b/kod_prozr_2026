import { useComputedColorScheme } from '@mantine/core';
import cytoscape, { type Core, type ElementDefinition } from 'cytoscape';
import { useEffect, useMemo, useRef } from 'react';
import type { GraphNode, OfficialGraph } from '@/shared/api';
import { buildStylesheet } from './graphStyle';

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

  useEffect(() => {
    clickRef.current = onNodeClick;
  }, [onNodeClick]);

  const elements = useMemo<ElementDefinition[]>(
    () => [
      ...graph.nodes.map((n) => ({
        data: { ...n, risk: n.risk ?? undefined },
        classes: n.id === rootId ? 'root' : undefined,
      })),
      ...graph.edges.map((e, i) => ({ data: { id: `e${i}`, ...e } })),
    ],
    [graph, rootId],
  );

  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: buildStylesheet(dark),
      layout: {
        name: 'cose',
        animate: false,
        padding: 30,
        nodeRepulsion: () => 9000,
        idealEdgeLength: () => 90,
      },
      minZoom: 0.3,
      maxZoom: 2.5,
      wheelSensitivity: 0.3,
    });
    cy.on('tap', 'node', (evt) => clickRef.current?.(evt.target.data() as GraphNode));
    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements, dark]);

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
        .filter((e) => ids.has(e.source().id()) && ids.has(e.target().id()))
        .removeClass('faded')
        .addClass('hl');
    });
  }, [highlight, elements, dark]);

  return (
    <div
      ref={containerRef}
      style={{
        height,
        width: '100%',
        borderRadius: 'var(--mantine-radius-md)',
        border: '1px solid var(--mantine-color-default-border)',
      }}
    />
  );
}
