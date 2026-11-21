import assert from 'node:assert/strict';
import { test } from 'node:test';
import { decodeWorkbench, toggleCase, COMPARISON_LIMIT } from '../src/features/workbench/model.ts';

const ref = (index: number) => ({
  id: `00000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
  name: `Служащий ${index}`,
});

test('saved workbench restores only valid unique references and ignores corrupt versions', () => {
  assert.deepEqual(decodeWorkbench('not json'), { version: 1, saved: [], comparison: [] });
  assert.deepEqual(decodeWorkbench(JSON.stringify({ version: 2, saved: [ref(1)] })).saved, []);
  const result = decodeWorkbench(
    JSON.stringify({
      version: 1,
      saved: [
        ref(1),
        ref(1),
        { id: 'bad', name: 'Неверный' },
        null,
        { ...ref(2), name: '  Второй  ' },
      ],
      comparison: [ref(1), ref(2), ref(3), ref(4)],
    }),
  );
  assert.equal(result.saved.length, 2);
  assert.equal(result.saved[1].name, 'Второй');
  assert.equal(result.comparison.length, COMPARISON_LIMIT);
});

test('comparison limit cannot be exceeded, selected cases can always be removed', () => {
  const items = [ref(1), ref(2), ref(3)];
  assert.deepEqual(toggleCase(items, ref(4), COMPARISON_LIMIT), items);
  assert.deepEqual(toggleCase(items, ref(2), COMPARISON_LIMIT), [ref(1), ref(3)]);
  assert.deepEqual(toggleCase([ref(1)], ref(2), COMPARISON_LIMIT), [ref(1), ref(2)]);
  assert.deepEqual(items, [ref(1), ref(2), ref(3)]);
});
