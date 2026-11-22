import assert from 'node:assert/strict';
import test from 'node:test';
import { mobilePositions } from '../src/features/relation-graph/graphModel.ts';
import type { OfficialGraph } from '../src/shared/api/types.ts';

test('mobile overview keeps every node in two columns without changing links', () => {
  const graph: OfficialGraph = {
    nodes: Array.from({ length: 12 }, (_, i) => ({
      id: String(i),
      type: 'person',
      label: `Person ${i}`,
    })),
    edges: [],
    truncated: false,
  };
  const before = JSON.stringify(graph);
  const positions = mobilePositions(graph, '3');
  assert.equal(Object.keys(positions).length, graph.nodes.length);
  assert.deepEqual(positions['3'], { x: 0, y: 0 });
  assert.equal(new Set(Object.values(positions).map((p) => p.x)).size, 2);
  assert.equal(
    new Set(Object.values(positions).map((p) => `${p.x},${p.y}`)).size,
    graph.nodes.length,
  );
  assert.equal(JSON.stringify(graph), before);
});
