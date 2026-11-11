import { Badge, Card, Group, SimpleGrid, Stack, Text } from '@mantine/core';
import type { StatsOverview } from '@/shared/api';
import {
  APPEAL_STATUS_COLORS,
  APPEAL_STATUS_LABELS,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
} from '@/shared/lib/labels';

export function StatCards({ stats }: { stats: StatsOverview }) {
  const flagsTotal = Object.values(stats.flags_by_severity).reduce((a, b) => a + b, 0);
  return (
    <SimpleGrid cols={{ base: 1, sm: 3 }}>
      <Card>
        <Text size="sm" c="dimmed">
          Служащие
        </Text>
        <Text fz={32} fw={700}>
          {stats.officials_total}
        </Text>
        <Text size="sm">
          с флагами риска: <b>{stats.officials_with_flags}</b>
        </Text>
      </Card>

      <Card>
        <Text size="sm" c="dimmed">
          Флаги риска
        </Text>
        <Text fz={32} fw={700}>
          {flagsTotal}
        </Text>
        <Group gap={6}>
          {(['high', 'medium', 'low'] as const).map((s) => (
            <Badge key={s} color={SEVERITY_COLORS[s]} variant="light">
              {SEVERITY_LABELS[s]}: {stats.flags_by_severity[s]}
            </Badge>
          ))}
        </Group>
      </Card>

      <Card>
        <Text size="sm" c="dimmed">
          Обращения граждан
        </Text>
        <Text fz={32} fw={700}>
          {stats.appeals_total}
        </Text>
        <Stack gap={4}>
          <Group gap={6}>
            {(['new', 'analyzed', 'routed', 'closed'] as const).map((s) => (
              <Badge key={s} color={APPEAL_STATUS_COLORS[s]} variant="light">
                {APPEAL_STATUS_LABELS[s]}: {stats.appeals_by_status[s]}
              </Badge>
            ))}
          </Group>
        </Stack>
      </Card>
    </SimpleGrid>
  );
}
