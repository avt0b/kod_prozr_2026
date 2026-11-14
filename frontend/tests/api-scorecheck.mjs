/** Run once against a freshly seeded, isolated API database. Creates one H1 appeal. */
import assert from 'node:assert/strict';
import { DEMO_APPEAL } from '../src/features/appeals/demoAppeal.ts';
const api = process.env.TEST_API_URL;
if (!api) throw new Error('Set TEST_API_URL to an isolated, freshly seeded backend');
const personId = '00000002-0000-4000-8000-000000000001';
async function json(path, options) {
  const response = await fetch(`${api}${path}`, options);
  assert.ok(response.ok, `${response.status} ${path}`);
  return response.json();
}
const before = (await json(`/officials/${personId}`)).risk.score;
const appeal = await json('/appeals', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: DEMO_APPEAL, channel: 'web' }),
});
assert.ok(appeal.linked_person_ids.includes(personId));
const after = (await json(`/officials/${personId}`)).risk.score;
assert.ok(
  after > before,
  `Expected an increase, got ${before} → ${after}. Run this check against a freshly seeded test database.`,
);
console.log(`PASS H1 risk increased ${before} → ${after}; category=${appeal.analysis.category}`);
