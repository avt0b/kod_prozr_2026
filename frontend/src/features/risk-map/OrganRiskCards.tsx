import { Badge, Card, Group, SimpleGrid, Stack, Text, UnstyledButton } from '@mantine/core';
import type { OrganRisk } from '@/shared/api';
import { RULE_TITLES } from '@/shared/lib/labels';
import { RiskScoreBadge } from '@/shared/ui';
import { HeatValue } from './HeatValue';
import type { RiskMetric } from './riskMapModel';

interface Props {
  organs: OrganRisk[];
  metric: RiskMetric;
  selectedId: string | null;
  onSelect: (organId: string | null) => void;
}

/** Сводка по органам. Клик выбирает орган (повторный — снимает выбор). */
export function OrganRiskCards({ organs, metric, selectedId, onSelect }: Props) {
  return (
    <SimpleGrid cols={{ base: 1, sm: 2, lg: Math.min(Math.max(organs.length, 1), 4) }}>
      {organs.map((o) => {
        const selected = o.organ_id === selectedId;
        return (
          <UnstyledButton
            key={o.organ_id}
            onClick={() => onSelect(selected ? null : o.organ_id)}
            aria-pressed={selected}
            aria-label={`Орган: ${o.organ}`}
          >
            <Card
              h="100%"
              style={{
                borderColor: selected ? 'var(--mantine-primary-color-filled)' : undefined,
                borderWidth: selected ? 2 : undefined,
              }}
            >
              <Group justify="space-between" align="flex-start" wrap="nowrap" gap="md">
                <Stack gap={6} style={{ minWidth: 0 }}>
                  <Text fw={600} lineClamp={2}>
                    {o.organ}
                  </Text>
                  <Text size="sm" c="dimmed">
                    {o.positions_total} должн. · {o.officials_total} служащих · с флагами{' '}
                    <b>{o.officials_with_flags}</b>
                  </Text>
                  <Group gap={6}>
                    <Text size="sm" c="dimmed">
                      макс. балл
                    </Text>
                    <RiskScoreBadge score={o.max_score} size="sm" />
                  </Group>
                  <Group gap={4}>
                    {o.top_rules.slice(0, 4).map((r) => (
                      <Badge
                        key={r.rule_code}
                        variant="light"
                        color="gray"
                        radius="sm"
                        title={RULE_TITLES[r.rule_code]}
                      >
                        {r.rule_code} × {r.count}
                      </Badge>
                    ))}
                  </Group>
                </Stack>
                <HeatValue agg={o} metric={metric} caption="по органу" />
              </Group>
            </Card>
          </UnstyledButton>
        );
      })}
    </SimpleGrid>
  );
}
