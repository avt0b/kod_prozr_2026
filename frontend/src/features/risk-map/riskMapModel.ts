import type { AuthorityKind, OrganRisk, PositionRisk, RiskAggregate } from '@/shared/api';

/** Чем окрашиваем тепловую карту и таблицу. */
export type RiskMetric = 'flagged_share' | 'avg_score' | 'max_score';

export const RISK_METRICS: RiskMetric[] = ['flagged_share', 'avg_score', 'max_score'];

export const METRIC_LABELS: Record<RiskMetric, string> = {
  flagged_share: 'Доля с флагами',
  avg_score: 'Средний балл',
  max_score: 'Максимальный балл',
};

/** 0.333 → «33%», баллы — как есть, с одним знаком после запятой. */
export function formatMetric(agg: Pick<RiskAggregate, RiskMetric>, metric: RiskMetric): string {
  if (metric === 'flagged_share') return `${Math.round(agg.flagged_share * 100)}%`;
  return (Math.round(agg[metric] * 10) / 10).toLocaleString('ru-RU');
}

export const AUTHORITY_ORDER: AuthorityKind[] = [
  'procurement',
  'permits',
  'inspection',
  'budget',
  'hr',
];

/** Значение метрики, приведённое к 0–1: доля как есть, баллы — из 100. */
export function metricIntensity(agg: Pick<RiskAggregate, RiskMetric>, metric: RiskMetric): number {
  const raw = metric === 'flagged_share' ? agg[metric] : agg[metric] / 100;
  return Number.isFinite(raw) ? Math.min(1, Math.max(0, raw)) : 0;
}

/**
 * Фон ячейки: красный с непрозрачностью по интенсивности. color-mix одинаково работает
 * в светлой и тёмной теме, потому что подмешивает прозрачность, а не белый.
 */
export function heatBackground(intensity: number): string {
  if (intensity <= 0) return 'transparent';
  const percent = Math.round(12 + Math.min(1, intensity) * 73);
  return `color-mix(in srgb, var(--mantine-color-red-7) ${percent}%, transparent)`;
}

/** На насыщенном фоне текст белый, иначе — цвет темы. */
export const heatTextColor = (intensity: number) => (intensity >= 0.55 ? 'white' : undefined);

/** Ячейка «вид полномочия × орган»: сводка по служащим всех должностей с этим полномочием. */
export interface HeatCell {
  positions: number;
  officials_total: number;
  officials_with_flags: number;
  flagged_share: number;
  avg_score: number;
  max_score: number;
}

export interface HeatRow {
  authority: AuthorityKind;
  cells: Record<string, HeatCell | null>;
}

function combine(items: PositionRisk[]): HeatCell | null {
  if (items.length === 0) return null;
  const total = items.reduce((sum, i) => sum + i.officials_total, 0);
  const flagged = items.reduce((sum, i) => sum + i.officials_with_flags, 0);
  // Средний балл должности взвешиваем числом её служащих: так получается среднее по людям.
  const scoreSum = items.reduce((sum, i) => sum + i.avg_score * i.officials_total, 0);
  return {
    positions: items.length,
    officials_total: total,
    officials_with_flags: flagged,
    flagged_share: total ? flagged / total : 0,
    avg_score: total ? Math.round((scoreSum / total) * 10) / 10 : 0,
    max_score: Math.max(0, ...items.map((i) => i.max_score)),
  };
}

/** Тепловая карта: строки — виды полномочий (только встречающиеся), столбцы — органы. */
export function buildAuthorityHeatmap(items: PositionRisk[], organs: OrganRisk[]): HeatRow[] {
  return AUTHORITY_ORDER.filter((kind) => items.some((i) => i.authorities.includes(kind))).map(
    (authority) => ({
      authority,
      cells: Object.fromEntries(
        organs.map((organ) => [
          organ.organ_id,
          combine(
            items.filter((i) => i.organ_id === organ.organ_id && i.authorities.includes(authority)),
          ),
        ]),
      ),
    }),
  );
}

export interface PositionFilter {
  organId?: string | null;
  authority?: AuthorityKind | null;
}

export function filterPositions(items: PositionRisk[], filter: PositionFilter): PositionRisk[] {
  return items.filter(
    (i) =>
      (!filter.organId || i.organ_id === filter.organId) &&
      (!filter.authority || i.authorities.includes(filter.authority)),
  );
}

/** По убыванию выбранной метрики, затем по среднему и максимальному баллу, затем по названию. */
export function sortPositions(items: PositionRisk[], metric: RiskMetric): PositionRisk[] {
  return [...items].sort(
    (a, b) =>
      b[metric] - a[metric] ||
      b.avg_score - a.avg_score ||
      b.max_score - a.max_score ||
      a.title.localeCompare(b.title, 'ru'),
  );
}
