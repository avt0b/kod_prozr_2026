import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Progress,
  SegmentedControl,
  Select,
  Skeleton,
  Stack,
  Switch,
  Text,
  Title,
  UnstyledButton,
} from '@mantine/core';
import { useMediaQuery, useReducedMotion } from '@mantine/hooks';
import {
  IconArrowLeft,
  IconArrowUpRight,
  IconChevronRight,
  IconLayoutSidebarRight,
  IconSparkles,
  IconX,
} from '@tabler/icons-react';
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router';
import { useOfficial, useOfficialGraph } from '@/features/officials/api';
import { ProfileSections } from '@/features/officials/ProfileSections';
import { CanvasMesh } from '@/features/relation-graph/CanvasMesh';
import { useGraphWorkspace } from '@/features/manual-graph/api';
import { withManualGraph } from '@/features/manual-graph/overlay';
import { ManualGraphEditor } from '@/features/manual-graph/ManualGraphEditor';
import { GraphEntityIcon } from '@/features/relation-graph/GraphLegend';
import { groupContracts } from '@/features/relation-graph/contractGroups';
import { CreateReportButton } from '@/features/reports/CreateReportButton';
import { FlagList } from '@/features/risk-flags/FlagList';
import { CaseActions } from '@/features/workbench/CaseActions';
import type { GraphNode, OfficialGraph, OfficialProfile, RiskFlag } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { formatMoney, RISK_LEVEL_COLORS, riskLevel } from '@/shared/lib/format';
import { KINSHIP_LABELS, NODE_TYPE_LABELS } from '@/shared/lib/labels';
import { AnimatedNumber } from '@/shared/ui/AnimatedNumber';
import { QueryState } from '@/shared/ui';
import './profile.css';

const RelationGraph = lazy(() =>
  import('@/features/relation-graph/RelationGraph').then((module) => ({
    default: module.RelationGraph,
  })),
);

const RISK_LABELS = {
  high: 'Высокий риск',
  medium: 'Средний риск',
  low: 'Низкий риск',
  none: 'Без флагов',
};

function ProfileDetails({
  profile,
  selectedFlag,
  onSelectFlag,
  showSummary = true,
}: {
  profile: OfficialProfile;
  showSummary?: boolean;
  selectedFlag: RiskFlag | null;
  onSelectFlag: (flag: RiskFlag | null) => void;
}) {
  const current = profile.appointments[0];
  const score = profile.risk.score;
  const level = riskLevel(score);
  const signal =
    selectedFlag ??
    profile.risk.flags.reduce<RiskFlag | undefined>(
      (highest, flag) => (!highest || flag.weight > highest.weight ? flag : highest),
      undefined,
    );

  return (
    <>
      {showSummary && (
        <section
          className="profile-inspector-section profile-risk-summary"
          aria-label="Оценка риска"
        >
          <Group justify="space-between" gap={8}>
            <Text size="xs" c="dimmed">
              Индекс риска конфликта
            </Text>
            <Badge
              className="profile-risk-label"
              data-level={level}
              color={RISK_LEVEL_COLORS[level]}
              variant="light"
            >
              <AnimatedNumber value={score} /> / 100 · {RISK_LABELS[level]}
            </Badge>
          </Group>
          <Progress
            className="profile-risk-bar"
            value={score}
            color={RISK_LEVEL_COLORS[level]}
            aria-label="Балл риска из 100"
            radius="xl"
          />
          <Text size="sm" className="profile-risk-lead" lineClamp={4}>
            {signal?.explanation ?? 'В профиле нет выявленных флагов риска.'}
          </Text>
          <Text size="xs" c="dimmed">
            Балл задаёт приоритет проверки и не подтверждает нарушение.
          </Text>
        </section>
      )}
      <div className="profile-actions">
        <div className="profile-primary-actions">
          <CreateReportButton personId={profile.person.id} compact />
          <Button
            className="profile-assistant-action"
            component={Link}
            to={routes.assistant()}
            state={{
              draft: `Какие риск-факторы и связи есть у служащего ${profile.person.full_name}?`,
            }}
            variant="default"
            leftSection={<IconSparkles size={17} aria-hidden />}
          >
            AI-анализ
          </Button>
        </div>
        <CaseActions person={{ id: profile.person.id, name: profile.person.full_name }} />
      </div>
      <section
        className="profile-inspector-section profile-flags"
        aria-labelledby="profile-risk-flags"
      >
        <Group justify="space-between" mb="xs">
          <Title id="profile-risk-flags" order={3} size="h5">
            Выявленные риск-факторы
          </Title>
          <Text size="xs" c="dimmed">
            {profile.risk.flags.length}
          </Text>
        </Group>
        <FlagList
          flags={profile.risk.flags}
          selectedId={selectedFlag?.id}
          expandedId={selectedFlag?.id}
          compact
          onSelect={onSelectFlag}
        />
      </section>
      {current && (
        <section className="profile-inspector-section">
          <Title order={3} size="h5" mb={5}>
            Должность и орган
          </Title>
          <Text size="sm" fw={600}>
            {current.position.title} · {current.position.department}
            {current.ended_at && ' (в прошлом)'}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            {current.organ.name}
          </Text>
        </section>
      )}
    </>
  );
}

function EntityDetails({ node, profile }: { node: GraphNode; profile: OfficialProfile }) {
  if (node.manual)
    return (
      <section className="profile-inspector-section">
        <Badge variant="light">Внесено аналитиком</Badge>
        <Text size="sm" mt="sm">
          Ручные сведения не проверены системой и не влияют на балл риска.
        </Text>
        {node.notes && (
          <Text size="sm" mt="sm">
            {node.notes}
          </Text>
        )}
        <Text size="sm" c="dimmed" mt="sm">
          Источник: {node.source || 'Не указан'}
        </Text>
      </section>
    );
  const relative = profile.relatives.find((item) => item.person.id === node.id);
  const company = profile.companies.find((link) => link.company.id === node.id);
  return (
    <section className="profile-inspector-section">
      <Text size="xs" fw={650} c="dimmed">
        {NODE_TYPE_LABELS[node.type]}
      </Text>
      <Text size="sm" fw={650} mt={4} style={{ whiteSpace: 'pre-line' }}>
        {node.label}
      </Text>
      {relative && (
        <Text size="sm" mt="xs">
          Связь со служащим: {KINSHIP_LABELS[relative.kind]}
        </Text>
      )}
      {company && (
        <Stack gap={4} mt="xs">
          <Text size="sm">ИНН {company.company.inn}</Text>
          <Text size="sm">Связь через {company.via_person_name}</Text>
          {company.share != null && <Text size="sm">Доля в компании: {company.share}%</Text>}
          {company.contracts_count != null && (
            <Text size="sm">Контрактов с органом: {company.contracts_count}</Text>
          )}
          {company.contracts_amount != null && (
            <Text size="sm">Сумма контрактов: {formatMoney(company.contracts_amount)}</Text>
          )}
        </Stack>
      )}
      {node.risk != null && (
        <Text size="sm" mt="xs">
          Балл риска: {node.risk} / 100
        </Text>
      )}
      {node.type === 'appeal' && (
        <Button
          component={Link}
          to={routes.appeal(node.id)}
          variant="light"
          size="xs"
          mt="sm"
          rightSection={<IconArrowUpRight size={15} />}
        >
          Открыть обращение
        </Button>
      )}
      {node.type === 'person' && node.risk != null && (
        <Button
          component={Link}
          to={routes.official(node.id)}
          variant="light"
          size="xs"
          mt="sm"
          rightSection={<IconArrowUpRight size={15} />}
        >
          Открыть профиль
        </Button>
      )}
    </section>
  );
}

function GraphEntities({
  graph,
  selectedId,
  onSelect,
}: {
  graph: OfficialGraph;
  selectedId: string;
  onSelect: (node: GraphNode) => void;
}) {
  const nodes = new Map(graph.nodes.map((node) => [node.id, node]));
  const related = graph.edges.flatMap((edge) => {
    const id =
      edge.source === selectedId ? edge.target : edge.target === selectedId ? edge.source : null;
    const node = id ? nodes.get(id) : undefined;
    return node ? [{ node, edge }] : [];
  });

  return (
    <section className="profile-inspector-section">
      <Title order={3} size="h5" mb="xs">
        Связанные сущности
      </Title>
      {related.length ? (
        related.map(({ node, edge }, index) => (
          <UnstyledButton
            className="profile-related-entity"
            key={`${node.id}:${edge.type}:${index}`}
            onClick={() => onSelect(node)}
          >
            <GraphEntityIcon type={node.type} />
            <span>
              <strong>{node.label}</strong>
              <small>
                {edge.label}
                {edge.manual ? ' · внесено аналитиком' : ''}
              </small>
            </span>
            <IconChevronRight size={15} aria-hidden />
          </UnstyledButton>
        ))
      ) : (
        <Text size="sm" c="dimmed">
          Прямых связей на холсте нет.
        </Text>
      )}
    </section>
  );
}

function ProfileCanvas({
  profile,
  graphQuery,
}: {
  profile: OfficialProfile;
  graphQuery: ReturnType<typeof useOfficialGraph>;
}) {
  const rootId = profile.person.id;
  const [flag, setFlag] = useState<RiskFlag | null>(null);
  const [selectedEntity, setEntity] = useState<GraphNode | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [grouped, setGrouped] = useState(true);
  const inspectorRef = useRef<HTMLElement>(null);
  const reopenRef = useRef<HTMLButtonElement>(null);
  const inspectorScrollRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();
  const stacked = useMediaQuery('(max-width: 55.99em)');
  const rawGraph = graphQuery.data;
  const workspace = useGraphWorkspace(rootId);
  const combinedGraph = useMemo(
    () => rawGraph && withManualGraph(rawGraph, workspace.workspace),
    [rawGraph, workspace.workspace],
  );
  const flagNodes = useMemo(() => flag?.evidence.map((item) => item.node_id), [flag]);
  const prepared = useMemo(
    () => (combinedGraph && grouped ? groupContracts(combinedGraph, flagNodes) : undefined),
    [combinedGraph, grouped, flagNodes],
  );
  const graph = prepared?.graph ?? combinedGraph;
  const entity = selectedEntity?.manual
    ? (graph?.nodes.find((node) => node.id === selectedEntity.id) ?? null)
    : selectedEntity;
  const flagHighlight = useMemo(
    () => flagNodes?.map((id) => prepared?.aliases.get(id) ?? id),
    [flagNodes, prepared],
  );
  useEffect(() => {
    if (inspectorScrollRef.current) inspectorScrollRef.current.scrollTop = 0;
  }, [entity?.id]);

  const selectEntity = (node: GraphNode) => {
    if (flagHighlight?.length && !flagHighlight.includes(node.id)) setFlag(null);
    setEntity(node.id === rootId ? null : node);
    setInspectorOpen(true);
    if (stacked) {
      requestAnimationFrame(() => {
        inspectorRef.current?.scrollIntoView({ behavior: reducedMotion ? 'instant' : 'smooth' });
      });
    }
  };
  const selectFlag = (next: RiskFlag | null) => {
    setFlag(next);
    if (next) {
      setEntity(null);
      setInspectorOpen(true);
    }
  };
  const signalPicker = profile.risk.flags.length > 0 && (
    <div
      className="workspace-signal-picker profile-glass"
      role="group"
      aria-label="Сигнал на графе"
    >
      <SegmentedControl
        size="xs"
        value={flag?.id ?? 'all'}
        onChange={(id) => {
          if (id === 'all') setEntity(null);
          selectFlag(profile.risk.flags.find((item) => item.id === id) ?? null);
        }}
        data={[
          { value: 'all', label: 'Все связи' },
          ...profile.risk.flags.map((item) => ({ value: item.id, label: item.rule_code })),
        ]}
      />
    </div>
  );

  return (
    <div className="profile-canvas-grid" data-inspector={inspectorOpen || undefined}>
      <section className="profile-graph-shell" aria-labelledby="profile-canvas-title">
        <div className="profile-canvas-context profile-glass">
          <Title order={2} id="profile-canvas-title" className="profile-title">
            {profile.person.full_name}
          </Title>
          <Text size="xs" className="profile-case-count" c="dimmed">
            Граф связей{graph && ` · ${graph.nodes.length} узлов · ${graph.edges.length} связей`}
          </Text>
          <Badge
            color="brand"
            variant="light"
            aria-hidden={!flag}
            style={{ visibility: flag ? 'visible' : 'hidden' }}
          >
            подсвечена цепочка {flag?.rule_code ?? 'R01'}
          </Badge>
          {!inspectorOpen && (
            <Button
              ref={reopenRef}
              variant="subtle"
              size="compact-xs"
              leftSection={<IconLayoutSidebarRight size={16} aria-hidden />}
              onClick={() => {
                setInspectorOpen(true);
                requestAnimationFrame(() => inspectorRef.current?.focus({ preventScroll: true }));
              }}
            >
              Инспектор
            </Button>
          )}
        </div>
        {!graph && signalPicker}
        <QueryState query={graphQuery}>
          {(data) => (
            <Suspense fallback={<Skeleton className="profile-graph-skeleton" />}>
              <RelationGraph
                graph={graph ?? data}
                rootId={rootId}
                rootSubtitle={profile.appointments[0]?.position.title}
                selectedId={entity?.id ?? rootId}
                onNodeClick={selectEntity}
                extraControls={<ManualGraphEditor controller={workspace} baseGraph={rawGraph} />}
                highlight={flagHighlight}
                signalPicker={
                  <>
                    {signalPicker}
                    <Switch
                      label="Группировать"
                      aria-label="Группировать контракты одного поставщика и заказчика"
                      checked={grouped}
                      size="xs"
                      onChange={(event) => {
                        setGrouped(event.currentTarget.checked);
                        setEntity(null);
                      }}
                    />
                  </>
                }
              />
            </Suspense>
          )}
        </QueryState>
      </section>
      {inspectorOpen && (
        <aside
          className="profile-inspector profile-glass"
          ref={inspectorRef}
          tabIndex={-1}
          aria-label="Инспектор графа"
        >
          <div className="profile-inspector-header" data-root={!entity || undefined}>
            <GraphEntityIcon type={entity?.type ?? 'person'} size={22} />
            <div role="status">
              <Text className="profile-inspector-type" size="xs" c="dimmed">
                {entity ? NODE_TYPE_LABELS[entity.type] : 'Служащий органа власти'}
              </Text>
              {entity ? (
                <Title order={3} size="h5">
                  {entity.label}
                </Title>
              ) : (
                <Text fw={690}>{profile.person.full_name}</Text>
              )}
            </div>
            <ActionIcon
              size={40}
              variant="subtle"
              color="gray"
              aria-label="Свернуть инспектор"
              onClick={() => {
                setInspectorOpen(false);
                requestAnimationFrame(() => reopenRef.current?.focus({ preventScroll: true }));
              }}
            >
              <IconX size={18} aria-hidden />
            </ActionIcon>
          </div>

          <div className="profile-inspector-scroll" ref={inspectorScrollRef}>
            <div className="profile-inspector-content" key={entity?.id ?? rootId}>
              {entity ? (
                <>
                  <EntityDetails node={entity} profile={profile} />
                  <Button
                    variant="light"
                    size="xs"
                    leftSection={<IconArrowLeft size={16} />}
                    onClick={() => setEntity(null)}
                  >
                    К данным служащего
                  </Button>
                  <ProfileDetails
                    profile={profile}
                    selectedFlag={flag}
                    onSelectFlag={selectFlag}
                    showSummary={false}
                  />
                </>
              ) : (
                <ProfileDetails profile={profile} selectedFlag={flag} onSelectFlag={selectFlag} />
              )}
              {graph && (
                <GraphEntities
                  graph={graph}
                  selectedId={entity?.id ?? rootId}
                  onSelect={selectEntity}
                />
              )}
              {!entity && <ProfileSections profile={profile} />}
            </div>
            {graph && (
              <Select
                label="Сущность на графе"
                placeholder="Выберите сущность"
                searchable
                allowDeselect={false}
                value={entity?.id ?? rootId}
                data={graph.nodes.map((node) => ({
                  value: node.id,
                  label: node.label.replaceAll('\n', ' '),
                }))}
                onChange={(id) => {
                  const node = graph.nodes.find((item) => item.id === id);
                  if (node) selectEntity(node);
                }}
              />
            )}
          </div>
        </aside>
      )}
    </div>
  );
}

export function OfficialProfilePage() {
  const { id = '' } = useParams();
  const { state } = useLocation();
  const search =
    typeof state?.ratingSearch === 'string' && state.ratingSearch.startsWith('?')
      ? (state.ratingSearch as string)
      : '';
  const profile = useOfficial(id);
  const graph = useOfficialGraph(id);

  return (
    <div className="official-profile">
      <CanvasMesh />
      <Button
        className="profile-back"
        component={Link}
        to={{ pathname: routes.officials(), search }}
        variant="default"
        leftSection={<IconArrowLeft size={17} aria-hidden />}
      >
        К рейтингу служащих
      </Button>
      <QueryState query={profile}>
        {(data) => <ProfileCanvas key={id} profile={data} graphQuery={graph} />}
      </QueryState>
    </div>
  );
}
