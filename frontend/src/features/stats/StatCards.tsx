import { Badge, Card, Group, SimpleGrid, Stack, Text } from '@mantine/core';
import type { OfficialListItem, StatsOverview } from '@/shared/api';
import { riskLevel } from '@/shared/lib/format';
import {
  APPEAL_STATUS_COLORS,
  APPEAL_STATUS_LABELS,
  SEVERITY_COLORS,
  SEVERITY_LABELS,
} from '@/shared/lib/labels';

export function StatCards({
  stats,
  leading,
}: {
  stats: StatsOverview;
  leading?: OfficialListItem;
}) {
  const flagsTotal = Object.values(stats.flags_by_severity).reduce((sum, count) => sum + count, 0);
  return (
    <Card>
      <SimpleGrid cols={{ base: 2, lg: leading ? 4 : 3 }} spacing="md" verticalSpacing="lg">
        <Stack gap={8} className="workspace-overview-stat">
          <Text size="sm" fw={620} c="dimmed">
            Служащие
          </Text>
          <Text className="workspace-overview-number" fz={34} fw={720}>
            {stats.officials_total}
          </Text>
          <Text size="xs" c="dimmed">
            С флагами риска: {stats.officials_with_flags}
          </Text>
        </Stack>

        <Stack gap={8} className="workspace-overview-stat">
          <Text size="sm" fw={620} c="dimmed">
            Флаги риска
          </Text>
          <Text className="workspace-overview-number" fz={34} fw={720}>
            {flagsTotal}
          </Text>
          <Group gap={4}>
            {(['high', 'medium', 'low'] as const).map((severity) => (
              <Badge key={severity} size="sm" color={SEVERITY_COLORS[severity]} variant="light">
                {SEVERITY_LABELS[severity]}: {stats.flags_by_severity[severity]}
              </Badge>
            ))}
          </Group>
        </Stack>

        <Stack gap={8} className="workspace-overview-stat">
          <Text size="sm" fw={620} c="dimmed">
            Обращения граждан
          </Text>
          <Text className="workspace-overview-number" fz={34} fw={720}>
            {stats.appeals_total}
          </Text>
          <Group gap={4}>
            {(['new', 'analyzed', 'routed', 'closed'] as const).map((status) => (
              <Badge key={status} size="sm" color={APPEAL_STATUS_COLORS[status]} variant="light">
                {APPEAL_STATUS_LABELS[status]}: {stats.appeals_by_status[status]}
              </Badge>
            ))}
          </Group>
        </Stack>

        {leading && (
          <Stack gap={8} className="workspace-overview-stat">
            <Text size="sm" fw={620} c="dimmed">
              Наивысший балл
            </Text>
            <Text
              className="workspace-overview-number workspace-profile-score"
              data-level={riskLevel(leading.risk_score)}
              fz={34}
              fw={720}
            >
              {leading.risk_score}
            </Text>
            <Text size="xs" c="dimmed">
              {leading.full_name}
            </Text>
          </Stack>
        )}
      </SimpleGrid>
    </Card>
  );
}
