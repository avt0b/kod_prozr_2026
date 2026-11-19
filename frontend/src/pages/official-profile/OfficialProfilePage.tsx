import {
  Anchor,
  Badge,
  Breadcrumbs,
  Card,
  Grid,
  Group,
  SegmentedControl,
  Skeleton,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconChevronRight } from '@tabler/icons-react';
import { lazy, Suspense, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { ProfileSections } from '@/features/officials/ProfileSections';
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
import './profile.css';

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
    <header className="profile-header">
      <Stack className="workspace-profile-identity profile-identity" gap={5}>
        <Title className="profile-title" order={2}>
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
      <div className="profile-header-side">
        <Group align="center" gap="sm" className="profile-header-controls">
          <Stack gap={4} align="flex-start">
            <Badge
              className="profile-risk-label"
              data-level={level}
              color={RISK_LEVEL_COLORS[level]}
              variant="light"
            >
              {RISK_LABELS[level]}
            </Badge>
            <Group gap={5} align="baseline" className="workspace-profile-score" data-level={level}>
              <Text className="profile-score-value" lh={1}>
                <AnimatedNumber value={profile.risk.score} />
              </Text>
              <Text size="xs" c="dimmed">
                из 100
              </Text>
            </Group>
          </Stack>
          <Group gap="xs" wrap="wrap" className="profile-actions">
            <CaseActions person={{ id: profile.person.id, name: profile.person.full_name }} />
            <CreateReportButton personId={profile.person.id} compact />
          </Group>
        </Group>
        <Text size="xs" c="dimmed">
          Балл задаёт приоритет проверки и не подтверждает нарушение.
        </Text>
      </div>
    </header>
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
    <div className="official-profile">
      <Breadcrumbs
        aria-label="Путь к профилю"
        className="profile-breadcrumbs"
        component="nav"
        separator={<IconChevronRight size={14} aria-hidden />}
      >
        <Anchor component={Link} to={routes.officials()} size="xs">
          К рейтингу служащих
        </Anchor>
        <Text size="xs" c="dimmed" aria-current="page">
          Профиль
        </Text>
      </Breadcrumbs>
      <QueryState query={profile}>
        {(p) => {
          const signal =
            selectedFlag ??
            p.risk.flags.reduce<RiskFlag | undefined>(
              (highest, flag) => (!highest || flag.weight > highest.weight ? flag : highest),
              undefined,
            );
          const signalPicker = p.risk.flags.length > 0 && (
            <GraphSignalPicker
              flags={p.risk.flags}
              selectedId={selectedFlag?.id}
              onSelect={setSelectedFlag}
            />
          );
          return (
            <>
              <ProfileHeader profile={p} />
              <Grid gutter="lg">
                <Grid.Col span={{ base: 12, lg: 8 }}>
                  <Card className="workspace-profile-graph">
                    <Group justify="space-between" gap="xs" mb="sm">
                      <Title order={3} size="h4">
                        Граф связей
                      </Title>
                      {selectedFlag && (
                        <Badge color="brand" variant="light">
                          подсвечена цепочка {selectedFlag.rule_code}
                        </Badge>
                      )}
                    </Group>
                    {!graph.data && signalPicker}
                    <QueryState query={graph}>
                      {(g) => (
                        <Suspense fallback={<Skeleton className="profile-graph-skeleton" />}>
                          <RelationGraph
                            graph={g}
                            rootId={id}
                            highlight={selectedFlag?.evidence.map((e) => e.node_id)}
                            onNodeClick={onNodeClick}
                            signalPicker={signalPicker}
                          />
                        </Suspense>
                      )}
                    </QueryState>
                    <div className="profile-graph-legend">
                      <GraphLegend />
                    </div>
                  </Card>
                </Grid.Col>
                <Grid.Col span={{ base: 12, lg: 4 }}>
                  <Card className="profile-flags">
                    <Group justify="space-between" mb="sm">
                      <Title order={3} size="h4">
                        Флаги риска
                      </Title>
                      <Badge
                        variant="light"
                        color="gray"
                        aria-label={`Флагов: ${p.risk.flags.length}`}
                      >
                        {p.risk.flags.length}
                      </Badge>
                    </Group>
                    <FlagList
                      flags={p.risk.flags}
                      selectedId={selectedFlag?.id}
                      expandedId={signal?.id}
                      onSelect={setSelectedFlag}
                    />
                  </Card>
                </Grid.Col>
              </Grid>

              <ProfileSections profile={p} />
            </>
          );
        }}
      </QueryState>
    </div>
  );
}
