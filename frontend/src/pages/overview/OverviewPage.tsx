import { Anchor, Button, Card, Divider, Group, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconArrowUpRight,
  IconBuilding,
  IconFiles,
  IconInbox,
  IconRefresh,
  IconUser,
  IconBuildingBank,
} from '@tabler/icons-react';
import { Link } from 'react-router';
import { useOfficialFlags, useOfficials } from '@/features/officials/api';
import { OfficialsTable } from '@/features/officials/OfficialsTable';
import { StatCards } from '@/features/stats/StatCards';
import { useOverview, useRecomputeRisk } from '@/features/stats/api';
import type { OfficialListItem, RiskFlag } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { formatDateTime } from '@/shared/lib/format';
import { NODE_TYPE_LABELS, RULE_TITLES } from '@/shared/lib/labels';
import { FlagBadge, PageHeader, QueryState } from '@/shared/ui';

const EVIDENCE_ICONS = {
  person: IconUser,
  company: IconBuilding,
  organ: IconBuildingBank,
  contract: IconFiles,
  appeal: IconInbox,
};

function RiskPriority({ official }: { official: OfficialListItem }) {
  const flags = useOfficialFlags(official.id);
  const flag = flags.data?.items.reduce<RiskFlag | null>(
    (strongest, item) => (!strongest || item.weight > strongest.weight ? item : strongest),
    null,
  );
  const evidence = flag && [...new Map(flag.evidence.map((node) => [node.node_id, node])).values()];
  return (
    <Card className="workspace-priority">
      <Group justify="space-between" align="flex-start" mb="sm">
        <Stack gap={8}>
          <Title order={3}>Приоритет проверки</Title>
          <Text size="sm" fw={650}>
            {official.full_name}
          </Text>
        </Stack>
        <Button
          component={Link}
          to={routes.official(official.id)}
          rightSection={<IconArrowUpRight size={16} />}
        >
          Открыть профиль
        </Button>
      </Group>
      {flag && (
        <Stack gap={10}>
          <Group gap={8}>
            <FlagBadge ruleCode={flag.rule_code} severity={flag.severity} />
            <Text fw={650} size="sm">
              {RULE_TITLES[flag.rule_code]}
            </Text>
          </Group>
          <Text c="dimmed" size="sm" lineClamp={2}>
            {flag.explanation}
          </Text>
          {!!evidence?.length && (
            <>
              <Divider my={3} />
              <Group gap={8} align="stretch" component="ol" className="workspace-evidence-list">
                {evidence.map((node) => {
                  const NodeIcon = EVIDENCE_ICONS[node.type];
                  return (
                    <Group
                      className="workspace-evidence-node"
                      key={node.node_id}
                      component="li"
                      gap={9}
                      wrap="nowrap"
                    >
                      <NodeIcon size={19} aria-hidden />
                      <Stack gap={2}>
                        <Text size="xs" fw={650} lineClamp={2}>
                          {node.label}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {NODE_TYPE_LABELS[node.type]}
                        </Text>
                      </Stack>
                    </Group>
                  );
                })}
              </Group>
            </>
          )}
        </Stack>
      )}
    </Card>
  );
}

export function OverviewPage() {
  const overview = useOverview();
  const top = useOfficials({ sort: '-risk_score', limit: 10, offset: 0 });
  const recompute = useRecomputeRisk();
  const leading = top.data?.items[0];

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
        <QueryState query={overview}>
          {(stats) => <StatCards stats={stats} leading={leading} />}
        </QueryState>
        {leading && leading.risk_score > 0 && <RiskPriority official={leading} />}

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
