import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildAuthorityHeatmap,
  filterPositions,
  formatMetric,
  heatBackground,
  metricIntensity,
  sortPositions,
} from '../src/features/risk-map/riskMapModel.ts';
import type { OrganRisk, PositionRisk } from '../src/shared/api/types.ts';

const position = (
  id: string,
  organ_id: string,
  authorities: PositionRisk['authorities'],
  stats: { total: number; flagged: number; avg: number; max: number },
): PositionRisk => ({
  position_id: id,
  title: `Должность ${id}`,
  department: 'Отдел',
  organ_id,
  organ: `Орган ${organ_id}`,
  is_corruption_risky: authorities.length > 0,
  authorities,
  risk_level: authorities.length ? 'high' : 'low',
  typical_risks: [],
  officials_total: stats.total,
  officials_with_flags: stats.flagged,
  flagged_share: stats.total ? stats.flagged / stats.total : 0,
  avg_score: stats.avg,
  max_score: stats.max,
  top_rules: [],
  top_officials: [],
});

const organ = (id: string): OrganRisk => ({
  organ_id: id,
  organ: `Орган ${id}`,
  positions_total: 0,
  officials_total: 0,
  officials_with_flags: 0,
  flagged_share: 0,
  avg_score: 0,
  max_score: 0,
  top_rules: [],
  top_officials: [],
});

const items = [
  position('buyer', 'A', ['procurement', 'budget'], { total: 1, flagged: 1, avg: 80, max: 80 }),
  position('clerk', 'A', ['procurement'], { total: 3, flagged: 0, avg: 0, max: 0 }),
  position('hr', 'B', ['hr'], { total: 2, flagged: 1, avg: 10, max: 20 }),
];

test('heatmap cells weight position averages by officials, not by positions', () => {
  const rows = buildAuthorityHeatmap(items, [organ('A'), organ('B')]);

  assert.deepEqual(
    rows.map((r) => r.authority),
    ['procurement', 'budget', 'hr'],
  );
  const procurementA = rows[0].cells.A!;
  assert.equal(procurementA.positions, 2);
  assert.equal(procurementA.officials_total, 4);
  assert.equal(procurementA.officials_with_flags, 1);
  assert.equal(procurementA.flagged_share, 0.25);
  assert.equal(procurementA.avg_score, 20); // (80·1 + 0·3) / 4, а не (80 + 0) / 2
  assert.equal(procurementA.max_score, 80);
  assert.equal(rows[0].cells.B, null);
});

test('filters combine organ and authority, sorting follows the chosen metric', () => {
  assert.deepEqual(
    filterPositions(items, { organId: 'A', authority: 'budget' }).map((i) => i.position_id),
    ['buyer'],
  );
  assert.equal(filterPositions(items, {}).length, 3);
  assert.deepEqual(
    sortPositions(items, 'flagged_share').map((i) => i.position_id),
    ['buyer', 'hr', 'clerk'],
  );
  assert.deepEqual(
    sortPositions(items, 'max_score').map((i) => i.position_id),
    ['buyer', 'hr', 'clerk'],
  );
});

test('metric intensity is clamped to 0–1 and zero cells stay uncoloured', () => {
  assert.equal(metricIntensity(items[0], 'flagged_share'), 1);
  assert.equal(metricIntensity(items[2], 'avg_score'), 0.1);
  assert.equal(metricIntensity({ ...items[0], max_score: 140 }, 'max_score'), 1);
  assert.equal(metricIntensity({ ...items[0], avg_score: NaN }, 'avg_score'), 0);
  assert.equal(heatBackground(0), 'transparent');
  assert.match(heatBackground(1), /color-mix\(in srgb, var\(--mantine-color-red-7\) 85%/);
  assert.equal(formatMetric(items[2], 'flagged_share'), '50%');
  assert.equal(formatMetric({ ...items[2], avg_score: 12.34 }, 'avg_score'), '12,3');
});
