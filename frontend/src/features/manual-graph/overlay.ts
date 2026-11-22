import type { OfficialGraph } from '@/shared/api';
import type { Workspace } from './api';

export function withManualGraph(base: OfficialGraph, workspace?: Workspace): OfficialGraph {
  if (!workspace) return base;
  const manualIds = new Set(workspace.nodes.map((node) => node.id));
  const identifier = (id: string) => (manualIds.has(id) ? `manual:${id}` : id);
  const nodes = [
    ...base.nodes,
    ...workspace.nodes.map((node) => ({
      id: identifier(node.id),
      type: node.kind,
      label: node.label,
      manual: true,
      notes: node.notes,
      source: node.source,
    })),
  ];
  const existing = new Set(nodes.map((node) => node.id));
  const edges = workspace.edges
    .map((edge) => ({
      id: edge.id,
      source: identifier(edge.source_id),
      target: identifier(edge.target_id),
      type: 'manual' as const,
      label: edge.label,
      manual: true,
      notes: edge.notes,
      sourceNote: edge.source,
    }))
    .filter((edge) => existing.has(edge.source) && existing.has(edge.target));
  return { ...base, nodes, edges: [...base.edges, ...edges] };
}
