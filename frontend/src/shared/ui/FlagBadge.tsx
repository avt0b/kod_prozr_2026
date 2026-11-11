import { Badge, Tooltip } from '@mantine/core';
import type { RuleCode, Severity } from '@/shared/api/types';
import { RULE_TITLES, SEVERITY_COLORS, SEVERITY_LABELS } from '@/shared/lib/labels';

interface Props {
  ruleCode: RuleCode;
  severity: Severity;
  withTitle?: boolean;
}

export function FlagBadge({ ruleCode, severity, withTitle = false }: Props) {
  return (
    <Tooltip label={`${RULE_TITLES[ruleCode]} · риск ${SEVERITY_LABELS[severity]}`} withArrow>
      <Badge color={SEVERITY_COLORS[severity]} variant="light" radius="sm">
        {withTitle ? `${ruleCode} · ${RULE_TITLES[ruleCode]}` : ruleCode}
      </Badge>
    </Tooltip>
  );
}
