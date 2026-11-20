import assert from 'node:assert/strict';
import test from 'node:test';
import { withManualGraph } from '../src/features/manual-graph/overlay.ts';
import { evidenceEdge } from '../src/features/relation-graph/graphModel.ts';
import { groupContracts } from '../src/features/relation-graph/contractGroups.ts';
import type { OfficialGraph } from '../src/shared/api/types.ts';
import type { Workspace } from '../src/features/manual-graph/api.ts';

test('manual overlays preserve sources, keep distinct links and never become flag evidence', () => {
  const base: OfficialGraph = {
    nodes: [{ id: 'root', type: 'person', label: 'Official' }],
    edges: [],
    truncated: false,
  };
  const workspace: Workspace = {
    id: 'workspace',
    official_id: 'root',
    owner_id: 'owner',
    owner_name: 'Owner',
    title: 'Notes',
    created_at: '',
    can_edit: true,
    shared_with: [],
    nodes: [
      { id: 'company', kind: 'company', label: 'Company', notes: 'Unverified', source: 'Note' },
    ],
    edges: [
      { id: 'a', source_id: 'root', target_id: 'company', label: 'First', notes: '', source: '' },
      { id: 'b', source_id: 'root', target_id: 'company', label: 'Second', notes: '', source: '' },
      {
        id: 'c',
        source_id: 'root',
        target_id: 'missing',
        label: 'Unavailable',
        notes: '',
        source: '',
      },
    ],
  };
  const original = JSON.stringify(base);
  const graph = withManualGraph(base, workspace);
  assert.equal(withManualGraph(base), base);
  assert.equal(JSON.stringify(base), original);
  assert.equal(graph.nodes[1].id, 'manual:company');
  assert.equal(graph.nodes[1].manual, true);
  assert.equal(graph.edges.length, 2);
  assert.equal(groupContracts(graph).graph.edges.length, 2);
  for (const edge of graph.edges)
    assert.equal(evidenceEdge(edge, new Set(graph.nodes.map((node) => node.id)), graph), false);
});
