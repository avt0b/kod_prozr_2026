import { Anchor, Button, Card, Group, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconRefresh, IconNetwork, IconMessageChatbot } from '@tabler/icons-react';
import { Link } from 'react-router';
import { useOfficials } from '@/features/officials/api';
import { OfficialsTable } from '@/features/officials/OfficialsTable';
import { StatCards } from '@/features/stats/StatCards';
import { FocusCase } from '@/features/stats/FocusCase';
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
      <section className="overview-intro" aria-label="Рабочее место аналитика">
        <div className="overview-intro-copy">
          <span className="editorial-eyebrow">Код прозрачности / аналитика</span>
          <h1>
            <span className="motion-headline-line">Видеть связи.</span>
            <span className="motion-headline-line">Понимать риски.</span>
          </h1>
          <p>
            От первого сигнала до доказательной цепочки. Служащие, закупки и обращения — в едином
            поле зрения.
          </p>
          <Group gap="sm" mt="xl">
            <Button
              component={Link}
              to={routes.riskMap()}
              leftSection={<IconNetwork size={18} />}
              size="md"
            >
              Исследовать риски
            </Button>
            <Button
              component={Link}
              to={routes.assistant()}
              variant="subtle"
              leftSection={<IconMessageChatbot size={18} />}
              size="md"
            >
              Задать вопрос
            </Button>
          </Group>
          <div className="overview-principle">
            <span aria-hidden="true">01 — 08</span> Восемь правил. Объяснимые сигналы.
            <br />
            Окончательное решение — за аналитиком.
          </div>
        </div>
        <QueryState query={top} isEmpty={(data) => data.items.length === 0}>
          {(data) => <FocusCase official={data.items[0]} />}
        </QueryState>
      </section>
      <Stack gap="xl">
        <QueryState query={overview}>{(stats) => <StatCards stats={stats} />}</QueryState>

        <Card className="overview-ranking">
          <Group justify="space-between" mb="lg">
            <div>
              <Text className="editorial-eyebrow" mb={6}>
                Приоритет проверки
              </Text>
              <Title order={3}>Топ-10 по риску</Title>
            </div>
            <Anchor component={Link} to={routes.officials()} size="sm">
              Весь рейтинг
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
