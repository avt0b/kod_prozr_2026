import { Badge, Card, Group, SimpleGrid, Stack, Text, UnstyledButton } from '@mantine/core';
import type { OrganRisk } from '@/shared/api';
import { RULE_TITLES } from '@/shared/lib/labels';
import { RiskScoreBadge } from '@/shared/ui';
import { formatMetric, type RiskMetric } from './riskMapModel';

interface Props {
  organs: OrganRisk[];
  metric: RiskMetric;
  selectedId: string | null;
  onSelect: (organId: string | null) => void;
}

/** Сводка по органам. Клик выбирает орган (повторный — снимает выбор). */
export function OrganRiskCards({ organs, metric, selectedId, onSelect }: Props) {
  return (
    <Card p={0}>
      <SimpleGrid
        cols={{ base: 1, sm: 2, lg: Math.min(Math.max(organs.length, 1), 4) }}
        spacing={0}
      >
        {organs.map((organ) => {
          const selected = organ.organ_id === selectedId;
          return (
            <UnstyledButton
              key={organ.organ_id}
              className="workspace-organ-stat"
              onClick={() => onSelect(selected ? null : organ.organ_id)}
              aria-pressed={selected}
              aria-label={`Орган: ${organ.organ}`}
            >
              <Stack gap={6} align="flex-start">
                <Text size="sm" fw={680}>
                  {organ.organ}
                </Text>
                <Text className="workspace-overview-number" fz={31} fw={720}>
                  {formatMetric(organ, metric)}
                </Text>
                <Text size="xs" c="dimmed">
                  {organ.positions_total} должн. · с флагами {organ.officials_with_flags} из{' '}
                  {organ.officials_total}
                </Text>
                <Group gap={6}>
                  <Text size="xs" c="dimmed">
                    Макс. балл
                  </Text>
                  <RiskScoreBadge score={organ.max_score} size="sm" />
                </Group>
                <Group gap={4}>
                  {organ.top_rules.slice(0, 4).map((rule) => (
                    <Badge
                      key={rule.rule_code}
                      variant="light"
                      color="gray"
                      radius="sm"
                      title={RULE_TITLES[rule.rule_code]}
                    >
                      {rule.rule_code} × {rule.count}
                    </Badge>
                  ))}
                </Group>
              </Stack>
            </UnstyledButton>
          );
        })}
      </SimpleGrid>
    </Card>
  );
}
