import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { RiskFlag, RuleCode, Severity } from '../src/shared/api/types.ts';
import { buildRuleMatrix } from '../src/features/workbench/ruleMatrix.ts';

function flag(code: RuleCode, severity: Severity): RiskFlag {
  return {
    id: `${code}-${severity}`,
    person_id: 'person',
    rule_code: code,
    severity,
    weight: 1,
    explanation: 'Объяснение',
    evidence: [],
  };
}
test('matrix distinguishes shared rules from partial rules and keeps absence explicit', () => {
  const rows = buildRuleMatrix([
    { risk: { flags: [flag('R01', 'high'), flag('R05', 'low')] } },
    { risk: { flags: [flag('R01', 'medium'), flag('R03', 'low')] } },
  ]);
  assert.deepEqual(
    rows.map((row) => [row.code, row.shared]),
    [
      ['R01', true],
      ['R03', false],
      ['R05', false],
    ],
  );
  assert.equal(rows[0].cells[0]?.severity, 'high');
  assert.equal(rows[0].cells[1]?.severity, 'medium');
  assert.equal(rows[1].cells[0], null);
  assert.equal(rows[2].cells[1], null);
});
test('multiple flags of a rule occupy one cell with a count and strongest severity', () => {
  const rows = buildRuleMatrix([{ risk: { flags: [flag('R05', 'low'), flag('R05', 'high')] } }]);
  assert.equal(rows.length, 1);
  assert.deepEqual(rows[0].cells, [{ count: 2, severity: 'high' }]);
  assert.equal(rows[0].shared, false);
  assert.deepEqual(buildRuleMatrix([{ risk: { flags: [] } }, { risk: { flags: [] } }]), []);
});
