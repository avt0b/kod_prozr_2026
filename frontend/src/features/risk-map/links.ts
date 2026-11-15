import type { RuleCode } from '@/shared/api';
import { routes } from '@/shared/config/routes';

/** Рейтинг служащих органа, при необходимости — только с флагом правила. */
export function ratingLink(organId: string, ruleCode?: RuleCode): string {
  const params = new URLSearchParams({ organ_id: organId });
  if (ruleCode) params.set('rule_code', ruleCode);
  return `${routes.officials()}?${params}`;
}
