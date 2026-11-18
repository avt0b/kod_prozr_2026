import { Badge, type BadgeProps } from '@mantine/core';
import { RISK_LEVEL_COLORS, riskLevel } from '@/shared/lib/format';

interface Props extends Omit<BadgeProps, 'color' | 'children'> {
  score: number;
}

/** Балл риска 0–100 с цветом уровня: ≥70 красный, ≥40 оранжевый, >0 жёлтый. */
export function RiskScoreBadge({ score, ...rest }: Props) {
  return (
    <Badge color={RISK_LEVEL_COLORS[riskLevel(score)]} variant="light" miw={44} {...rest}>
      {score}
    </Badge>
  );
}
