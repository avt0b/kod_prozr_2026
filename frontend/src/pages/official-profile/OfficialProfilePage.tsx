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
import { FlagList } from '@/features/risk-flags/FlagList';
import type { GraphNode, OfficialProfile, RiskFlag } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { RISK_LEVEL_COLORS, riskLevel } from '@/shared/lib/format';
import { RULE_TITLES, SEVERITY_COLORS } from '@/shared/lib/labels';
import { QueryState } from '@/shared/ui';
import { useLiquidGlass } from '@/shared/ui/useLiquidGlass';

// Cytoscape тяжёлый (~400 КБ) — грузим отдельным чанком только на странице профиля
const RelationGraph = lazy(() =>
  import('@/features/relation-graph/RelationGraph').then((m) => ({ default: m.RelationGraph })),
);

function ProfileHeader({ profile }: { profile: OfficialProfile }) {
  const current = profile.appointments[0];
  const level = riskLevel(profile.risk.score);
  return (
    <Card mb="lg">
      <Group justify="space-between" align="center" wrap="wrap">
        <Group gap="lg" wrap="nowrap" className="workspace-profile-identity">
          <Stack
            gap={0}
            align="center"
            justify="center"
            className="workspace-profile-score"
            style={
              {
                '--score-ink': `var(--mantine-color-${RISK_LEVEL_COLORS[level]}-filled)`,
              } as CSSProperties
            }
          >
            <Text fz={30} fw={700} lh={1}>
              {profile.risk.score}
            </Text>
            <Text size="xs" c="dimmed">
              из 100
            </Text>
          </Stack>
          <Stack gap={4}>
            <Title order={2}>{profile.person.full_name}</Title>
            {current && (
              <Text size="sm">
                {current.position.title}, {current.position.department.toLowerCase()} ·{' '}
                {current.organ.name}
                {current.ended_at && ' (в прошлом)'}
              </Text>
            )}
            <Group gap={4}>
              {profile.risk.flags.map((f) => (
                <Badge key={f.id} size="sm" variant="light" color={SEVERITY_COLORS[f.severity]}>
                  {f.rule_code} · {RULE_TITLES[f.rule_code]}
                </Badge>
              ))}
            </Group>
          </Stack>
        </Group>
        <CreateReportButton personId={profile.person.id} />
      </Group>
    </Card>
  );
}

function RiskSummary({ signal }: { signal: RiskFlag }) {
  const color = SEVERITY_COLORS[signal.severity];
  return (
    <Card
      className="workspace-risk-summary"
      mb="lg"
      style={{ '--summary-accent': `var(--mantine-color-${color}-light-color)` } as CSSProperties}
    >
      <Group justify="space-between" gap="xs" mb="xs">
        <Title order={3}>Что повлияло на оценку</Title>
        <Badge color={color} variant="light">
          {signal.rule_code} · {RULE_TITLES[signal.rule_code]}
        </Badge>
      </Group>
      <Text size="sm">{signal.explanation}</Text>
      {signal.legal_ref && (
        <Text size="xs" c="dimmed" mt="xs">
          {signal.legal_ref}
        </Text>
      )}
    </Card>
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
              {signal && <RiskSummary key={signal.id} signal={signal} />}
              <Grid gutter="lg">
                <Grid.Col span={{ base: 12, lg: 7 }}>
                  <Card className="workspace-profile-graph">
                    <Group justify="space-between" mb="sm">
                      <Title order={4}>Граф связей</Title>
                      {selectedFlag && (
                        <Badge color="red" variant="light">
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
                            <Center h={520}>
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
                <Grid.Col span={{ base: 12, lg: 5 }}>
                  <Title order={4} mb="sm">
                    Флаги риска ({p.risk.flags.length})
                  </Title>
                  <FlagList
                    flags={p.risk.flags}
                    selectedId={selectedFlag?.id}
                    onSelect={setSelectedFlag}
                  />
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
