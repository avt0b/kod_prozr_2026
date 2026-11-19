import type { RiskFlag, RuleCode, Severity } from '@/shared/api';

const severityOrder: Record<Severity, number> = { low: 1, medium: 2, high: 3 };
export interface RuleCell {
  count: number;
  severity: Severity;
}
export interface RuleRow {
  code: RuleCode;
  cells: (RuleCell | null)[];
  shared: boolean;
}

/** Count people with each rule, preserving multiple flags and the strongest severity per person. */
export function buildRuleMatrix(profiles: { risk: { flags: RiskFlag[] } }[]): RuleRow[] {
  const codes = [
    ...new Set(profiles.flatMap((profile) => profile.risk.flags.map((flag) => flag.rule_code))),
  ].sort();
  return codes
    .map((code) => {
      const cells = profiles.map((profile) => {
        const flags = profile.risk.flags.filter((flag) => flag.rule_code === code);
        if (!flags.length) return null;
        const severity = flags.reduce<Severity>(
          (highest, flag) =>
            severityOrder[flag.severity] > severityOrder[highest] ? flag.severity : highest,
          'low',
        );
        return { count: flags.length, severity };
      });
      return { code, cells, shared: cells.length > 1 && cells.every(Boolean) };
    })
    .sort((a, b) => Number(b.shared) - Number(a.shared) || a.code.localeCompare(b.code));
}
