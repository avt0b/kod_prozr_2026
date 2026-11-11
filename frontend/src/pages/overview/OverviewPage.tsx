import { Anchor, Button, Card, Group, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconRefresh } from '@tabler/icons-react';
import { Link } from 'react-router';
import { useOfficials } from '@/features/officials/api';
import { OfficialsTable } from '@/features/officials/OfficialsTable';
import { StatCards } from '@/features/stats/StatCards';
import { useOverview, useRecomputeRisk } from '@/features/stats/api';
import { routes } from '@/shared/config/routes';
import { formatDateTime } from '@/shared/lib/format';
import { PageHeader, QueryState } from '@/shared/ui';

export function OverviewPage() {
  const overview = useOverview();
  const top = useOfficials({ sort: '-risk_score', limit: 10, offset: 0 });
  const recompute = useRecomputeRisk();

  return (
    <>
      <PageHeader
        title="Обзор"
        description={
          overview.data && `Баллы риска рассчитаны: ${formatDateTime(overview.data.computed_at)}`
        }
        actions={
          <Button
            variant="light"
            leftSection={<IconRefresh size={16} />}
            loading={recompute.isPending}
            onClick={() =>
              recompute.mutate(undefined, {
                onSuccess: (r) =>
                  notifications.show({
                    color: 'teal',
                    message: `Пересчитано: ${r.officials_processed} служащих, ${r.flags_total} флагов`,
                  }),
              })
            }
          >
            Пересчитать риски
          </Button>
        }
      />
      <Stack gap="lg">
        <QueryState query={overview}>{(stats) => <StatCards stats={stats} />}</QueryState>

        <Card>
          <Group justify="space-between" mb="sm">
            <Title order={4}>Топ-10 по риску</Title>
            <Anchor component={Link} to={routes.officials()} size="sm">
              Весь рейтинг →
            </Anchor>
          </Group>
          <QueryState query={top} isEmpty={(d) => d.items.length === 0}>
            {(data) => <OfficialsTable items={data.items} />}
          </QueryState>
          <Text size="xs" c="dimmed" mt="sm">
            Балл риска — сигнал для проверки, а не вывод о правонарушении. Решение принимает
            аналитик.
          </Text>
        </Card>
      </Stack>
    </>
  );
}
