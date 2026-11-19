import {
  Anchor,
  Badge,
  Card,
  Center,
  Grid,
  Group,
  Loader,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { lazy, Suspense, useState, type CSSProperties } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import {
  AppointmentsSection,
  AuthoritiesSection,
  CompaniesSection,
  RelativesSection,
} from '@/features/officials/ProfileSections';
import { useOfficial, useOfficialGraph } from '@/features/officials/api';
import { GraphLegend } from '@/features/relation-graph/GraphLegend';
import { CreateReportButton } from '@/features/reports/CreateReportButton';
import { CaseActions } from '@/features/workbench/CaseActions';
import { FlagList } from '@/features/risk-flags/FlagList';
import type { GraphNode, OfficialProfile, RiskFlag } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { RISK_LEVEL_COLORS, riskLevel } from '@/shared/lib/format';
import { QueryState } from '@/shared/ui';
import { useLiquidGlass } from '@/shared/ui/useLiquidGlass';
import { AnimatedNumber } from '@/shared/ui/AnimatedNumber';

// Cytoscape тяжёлый (~400 КБ) — грузим отдельным чанком только на странице профиля
const RelationGraph = lazy(() =>
  import('@/features/relation-graph/RelationGraph').then((m) => ({ default: m.RelationGraph })),
);

const RISK_LABELS = {
  high: 'Высокий риск',
  medium: 'Средний риск',
  low: 'Низкий риск',
  none: 'Без флагов',
};

function ProfileHeader({ profile }: { profile: OfficialProfile }) {
  const current = profile.appointments[0];
  const level = riskLevel(profile.risk.score);
  return (
    <Group justify="space-between" align="center" gap="md" mb="xl">
      <Stack className="workspace-profile-name workspace-profile-identity" gap={5}>
        <Title className="workspace-profile-title" order={2}>
          {profile.person.full_name}
        </Title>
        {current && (
          <>
            <Text size="sm" fw={620}>
              {current.position.title} · {current.position.department}
              {current.ended_at && ' (в прошлом)'}
            </Text>
            <Text c="dimmed" size="sm">
              {current.organ.name}
            </Text>
          </>
        )}
      </Stack>
      <Group gap="md" className="workspace-profile-tools">
        <Stack gap={4} align="flex-start">
          <Badge color={RISK_LEVEL_COLORS[level]} variant="light">
            {RISK_LABELS[level]}
          </Badge>
          <Group
            gap={5}
            align="baseline"
            className="workspace-profile-score"
            data-level={level}
            style={{ '--score-ink': 'currentColor' } as CSSProperties}
          >
            <Text fz={26} fw={730} lh={1}>
              <AnimatedNumber value={profile.risk.score} />
            </Text>
            <Text size="xs" c="dimmed">
              из 100
            </Text>
          </Group>
        </Stack>
        <CaseActions person={{ id: profile.person.id, name: profile.person.full_name }} />
        <CreateReportButton personId={profile.person.id} compact />
      </Group>
      <Text size="sm" c="dimmed" w="100%">
        Балл задаёт приоритет проверки и не подтверждает нарушение.
      </Text>
    </Group>
  );
}

function GraphSignalPicker({
  flags,
  selectedId,
  onSelect,
}: {
  flags: RiskFlag[];
  selectedId: string | undefined;
  onSelect: (flag: RiskFlag | null) => void;
}) {
  const glass = useLiquidGlass<HTMLDivElement>();

  return (
    <div
      className="workspace-signal-picker workspace-glass"
      role="group"
      aria-label="Сигнал на графе"
      {...glass.props}
    >
      {glass.lens}
      <SegmentedControl
        size="xs"
        value={selectedId ?? 'all'}
        onChange={(id) => onSelect(flags.find((flag) => flag.id === id) ?? null)}
        data={[
          { value: 'all', label: 'Все связи' },
          ...flags.map((flag) => ({ value: flag.id, label: flag.rule_code })),
        ]}
      />
    </div>
  );
}

export function OfficialProfilePage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const profile = useOfficial(id);
  const graph = useOfficialGraph(id);
  // Выбор флага привязан к служащему: при переходе на другой профиль подсветка сбрасывается
  const [selected, setSelected] = useState<{ personId: string; flag: RiskFlag } | null>(null);
  const selectedFlag = selected?.personId === id ? selected.flag : null;
  const setSelectedFlag = (flag: RiskFlag | null) =>
    setSelected(flag ? { personId: id, flag } : null);

  const onNodeClick = (node: GraphNode) => {
    if (node.type === 'person' && node.risk != null && node.id !== id)
      navigate(routes.official(node.id));
    if (node.type === 'appeal') navigate(routes.appeal(node.id));
  };

  return (
    <>
      <Anchor component={Link} to={routes.officials()} size="sm" mb="sm" display="inline-block">
        ← К рейтингу
      </Anchor>
      <QueryState query={profile}>
        {(p) => {
          const signal =
            selectedFlag ??
            p.risk.flags.reduce<RiskFlag | null>(
              (highest, flag) => (!highest || flag.weight > highest.weight ? flag : highest),
              null,
            );
          return (
            <>
              <ProfileHeader profile={p} />
              <Grid gutter="lg">
                <Grid.Col span={{ base: 12, lg: 8 }}>
                  <Card className="workspace-profile-graph">
                    <Group justify="space-between" mb="sm">
                      <Title order={4}>Граф связей</Title>
                      {selectedFlag && (
                        <Badge color="brand" variant="light">
                          подсвечена цепочка {selectedFlag.rule_code}
                        </Badge>
                      )}
                    </Group>
                    {p.risk.flags.length > 0 && (
                      <GraphSignalPicker
                        flags={p.risk.flags}
                        selectedId={selectedFlag?.id}
                        onSelect={setSelectedFlag}
                      />
                    )}
                    <QueryState query={graph}>
                      {(g) => (
                        <Suspense
                          fallback={
                            <Center h={400}>
                              <Loader />
                            </Center>
                          }
                        >
                          <RelationGraph
                            graph={g}
                            rootId={id}
                            highlight={selectedFlag?.evidence.map((e) => e.node_id)}
                            onNodeClick={onNodeClick}
                          />
                        </Suspense>
                      )}
                    </QueryState>
                    <Stack gap={4} mt="sm">
                      <GraphLegend />
                      <Text size="xs" c="dimmed">
                        Выберите флаг, чтобы подсветить его связи. Нажмите на узел служащего или
                        обращения, чтобы открыть карточку.
                      </Text>
                    </Stack>
                  </Card>
                </Grid.Col>
                <Grid.Col span={{ base: 12, lg: 4 }}>
                  <Card>
                    <Title order={4} mb="sm">
                      Флаги риска ({p.risk.flags.length})
                    </Title>
                    <FlagList
                      flags={p.risk.flags}
                      selectedId={selectedFlag?.id}
                      expandedId={signal?.id}
                      onSelect={setSelectedFlag}
                    />
                  </Card>
                </Grid.Col>
              </Grid>

              <SimpleGrid cols={{ base: 1, md: 2 }} mt="lg">
                <AppointmentsSection profile={p} />
                <AuthoritiesSection profile={p} />
                <RelativesSection profile={p} />
                <CompaniesSection profile={p} />
              </SimpleGrid>
            </>
          );
        }}
      </QueryState>
    </>
  );
}
