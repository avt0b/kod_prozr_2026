import assert from 'node:assert/strict';
import test from 'node:test';
import { entityRanges } from '../src/features/appeals/entityRanges.ts';
import { labelAmount, groupContracts } from '../src/features/relation-graph/contractGroups.ts';
import { evidenceEdge, graphElements } from '../src/features/relation-graph/graphModel.ts';
import {
  normalizeFlag,
  normalizeProfile,
  normalizeOfficial,
} from '../src/shared/api/officialAdapters.ts';
import type { AppealEntity, OfficialGraph } from '../src/shared/api/types.ts';
import type { WireFlag, WireProfile } from '../src/shared/api/officialAdapters.ts';

const entity = (text: string, start: number, end: number): AppealEntity => ({
  type: 'person',
  text,
  start,
  end,
});

test('quotes and newlines preserve exact source ranges', () => {
  const text = '«Соколов»\nсказал: "Проверить"';
  assert.deepEqual(entityRanges(text, [entity('Соколов', 1, 8)]), [entity('Соколов', 1, 8)]);
});
test('Python code point offsets after emoji become UTF-16 offsets', () => {
  const text = '📨 «Соколов»\n';
  assert.deepEqual(entityRanges(text, [entity('Соколов', 3, 10)]), [entity('Соколов', 4, 11)]);
});
test('UTF-16 offsets after emoji also remain valid', () => {
  assert.equal(entityRanges('📨 Соколов', [entity('Соколов', 3, 10)])[0].start, 3);
});
test('malformed, overlapping and mismatched offsets never mark other text', () => {
  const result = entityRanges('Соколов', [
    entity('Соколов', 0, 7),
    entity('око', 1, 4),
    entity('другое', 0, 6),
    entity('С', -1, 1),
    entity('С', NaN, 1),
    entity('С', 0.5, 1),
  ]);
  assert.deepEqual(result, [entity('Соколов', 0, 7)]);
});
test('repeated entity text uses offsets rather than the first occurrence', () => {
  assert.equal(entityRanges('Иванов и Иванов', [entity('Иванов', 9, 15)])[0].start, 9);
});
const graph: OfficialGraph = {
  nodes: [
    { id: 'person', type: 'person', label: 'Служащий' },
    { id: 'organ', type: 'organ', label: 'Орган' },
    { id: 'company', type: 'company', label: 'Компания' },
    ...Array.from({ length: 5 }, (_, i) => ({
      id: `c${i}`,
      type: 'contract' as const,
      label: `№12345, ${i + 1},5 млн руб.`,
    })),
  ],
  edges: [
    { source: 'person', target: 'organ', type: 'works_in', label: 'работает' },
    ...Array.from({ length: 5 }, (_, i) => [
      { source: 'company', target: `c${i}`, type: 'supplier' as const, label: 'поставщик' },
      { source: `c${i}`, target: 'organ', type: 'customer' as const, label: 'заказчик' },
    ]).flat(),
  ],
};
test('contract groups preserve supplier/customer and approximate total', () => {
  const grouped = groupContracts(graph);
  const node = grouped.graph.nodes.find((n) => n.type === 'contract')!;
  assert.match(node.label, /5 контрактов/);
  assert.match(node.label, /17,5 млн/);
  assert.equal(grouped.aliases.size, 5);
  assert.equal(grouped.graph.edges.length, 3);
});
test('unknown amounts do not become fabricated zero totals', () => {
  const changed = {
    ...graph,
    nodes: graph.nodes.map((n) => (n.id === 'c0' ? { ...n, label: 'Сумма не указана' } : n)),
  };
  assert.equal(groupContracts(changed).aliases.size, 0);
});
test('amount parsing handles both backend and mock labels', () => {
  assert.equal(labelAmount('№123, 12,5 млн руб.'), 12_500_000);
  assert.equal(labelAmount('Контракт № …123 · 9,5 млн ₽'), 9_500_000);
  assert.equal(labelAmount('№123, 250 тыс. руб.'), 250_000);
  assert.equal(labelAmount('№123'), null);
});
test('R01 highlights contract links without the employment shortcut', () => {
  const ids = new Set(graph.nodes.map((n) => n.id));
  assert.equal(evidenceEdge(graph.edges[0], ids, graph), false);
  assert.equal(evidenceEdge(graph.edges[1], ids, graph), true);
  assert.equal(evidenceEdge(graph.edges[1], new Set(['company']), graph), false);
});
test('invalid dangling graph edges cannot crash Cytoscape', () => {
  const elements = graphElements({
    ...graph,
    edges: [
      ...graph.edges,
      { source: 'absent', target: 'person', type: 'kinship', label: 'ошибка' },
    ],
  });
  assert.equal(elements.length, graph.nodes.length + graph.edges.length);
  assert.equal(new Set(elements.map((e) => e.data.id)).size, elements.length);
});
test('backend evidence IDs normalize to the frontend graph ID', () => {
  const flag = { evidence: [{ id: 'node', type: 'person', label: 'Служащий' }] } as WireFlag;
  assert.equal(normalizeFlag(flag).evidence[0].node_id, 'node');
});
test('backend profile does not fabricate absent company totals', () => {
  const profile = {
    person: { id: 'p', full_name: 'Соколов' },
    appointments: [],
    relatives: [],
    authorities: [],
    risk: { score: 50, flags: [] },
    companies: [
      {
        person_id: 'p',
        company_id: 'c',
        company_name: 'ООО',
        company_inn: '123',
        company_status: 'active',
        role: 'founder',
        started_at: '2026-01-01',
      },
    ],
  } as WireProfile;
  assert.equal(normalizeProfile(profile, []).companies[0].company.name, 'ООО');
  assert.equal(normalizeProfile(profile, []).companies[0].contracts_count, undefined);
});
test('backend nullable position and organ render without React object errors', () => {
  const result = normalizeOfficial({
    id: 'p',
    full_name: 'Иванов',
    position: null,
    organ: null,
    organ_id: '',
    risk_score: 0,
    top_flags: [],
  });
  assert.equal(typeof result.organ, 'string');
  assert.equal(typeof result.position, 'string');
});

test('partial evidence never highlights unrelated grouped contracts', () => {
  assert.equal(groupContracts(graph, ['c0']).aliases.size, 0);
});
