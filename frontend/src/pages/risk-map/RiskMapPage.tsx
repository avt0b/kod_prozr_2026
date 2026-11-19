import { Badge, Button, Card, Group, SegmentedControl, Stack, Text, Title } from '@mantine/core';
import { IconX } from '@tabler/icons-react';
import { useSearchParams } from 'react-router';
import { AuthorityHeatmap } from '@/features/risk-map/AuthorityHeatmap';
import { OrganRiskCards } from '@/features/risk-map/OrganRiskCards';
import { PositionRiskDrawer } from '@/features/risk-map/PositionRiskDrawer';
import { PositionRiskTable } from '@/features/risk-map/PositionRiskTable';
import { useRiskMap } from '@/features/risk-map/api';
import {
  AUTHORITY_ORDER,
  METRIC_LABELS,
  RISK_METRICS,
  filterPositions,
  sortPositions,
  type RiskMetric,
} from '@/features/risk-map/riskMapModel';
import type { AuthorityKind } from '@/shared/api';
import { formatDateTime } from '@/shared/lib/format';
import { AUTHORITY_LABELS } from '@/shared/lib/labels';
import { PageHeader, QueryState } from '@/shared/ui';

const parseMetric = (value: string | null): RiskMetric =>
  RISK_METRICS.includes(value as RiskMetric) ? (value as RiskMetric) : 'flagged_share';

const parseAuthority = (value: string | null): AuthorityKind | null =>
  AUTHORITY_ORDER.includes(value as AuthorityKind) ? (value as AuthorityKind) : null;

/** Вариант D: где сосредоточен риск — по должностям, полномочиям и органам. Фильтры в URL. */
export function RiskMapPage() {
  const [params, setParams] = useSearchParams();
  const organId = params.get('organ_id');
  const authority = parseAuthority(params.get('authority'));
  const metric = parseMetric(params.get('metric'));
  const positionId = params.get('position');
  // Карту берём целиком: сводка и тепловая карта показывают все органы, фильтр — на клиенте.
  const map = useRiskMap();

  const update = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v === null || v === '') next.delete(k);
      else next.set(k, v);
    }
    setParams(next, { replace: true });
  };

  return (
    <>
      <PageHeader
        title="Карта рисков должностей"
        description={
          map.data &&
          `Риск по полномочиям должностей и флагам служащих на них. Баллы рассчитаны: ${formatDateTime(map.data.computed_at)}`
        }
        actions={
          <SegmentedControl
            size="xs"
            className="workspace-risk-metrics"
            value={metric}
            onChange={(v) => update({ metric: v === 'flagged_share' ? null : v })}
            data={RISK_METRICS.map((m) => ({
              value: m,
              label: m === 'max_score' ? 'Макс. балл' : METRIC_LABELS[m],
            }))}
          />
        }
      />
      <QueryState
        query={map}
        isEmpty={(d) => d.items.length === 0}
        empty="Нет служащих с назначениями: карта пуста"
      >
        {(data) => {
          const items = sortPositions(filterPositions(data.items, { organId, authority }), metric);
          const opened = data.items.find((p) => p.position_id === positionId) ?? null;
          const organName = data.organs.find((o) => o.organ_id === organId)?.organ;
          return (
            <Stack gap="lg">
              <OrganRiskCards
                organs={data.organs}
                metric={metric}
                selectedId={organId}
                onSelect={(id) => update({ organ_id: id })}
              />

              <Card>
                <Group justify="space-between" mb="sm">
                  <Title order={4}>Полномочия × органы</Title>
                  <Text size="sm" c="dimmed">
                    Цвет — {METRIC_LABELS[metric].toLowerCase()}. Клик по ячейке оставляет в таблице
                    её должности
                  </Text>
                </Group>
                <AuthorityHeatmap
                  items={data.items}
                  organs={data.organs}
                  metric={metric}
                  selected={{ organId, authority }}
                  onSelect={(organ, kind) => update({ organ_id: organ, authority: kind })}
                />
              </Card>

              <Card p={0}>
                <Group justify="space-between" p="md" pb="xs">
                  <Group gap="xs">
                    <Title order={4}>Должности</Title>
                    {organName && (
                      <Badge variant="light" size="lg" tt="none">
                        {organName}
                      </Badge>
                    )}
                    {authority && (
                      <Badge variant="light" color="gray" size="lg" tt="none">
                        {AUTHORITY_LABELS[authority]}
                      </Badge>
                    )}
                    {(organId || authority) && (
                      <Button
                        size="compact-sm"
                        variant="subtle"
                        leftSection={<IconX size={14} />}
                        onClick={() => update({ organ_id: null, authority: null })}
                      >
                        Сбросить
                      </Button>
                    )}
                  </Group>
                  <Text size="sm" c="dimmed">
                    {items.length} из {data.total} · клик по строке — типовые риски и служащие
                  </Text>
                </Group>
                {items.length === 0 ? (
                  <Text c="dimmed" ta="center" py="xl">
                    По выбранным фильтрам должностей нет
                  </Text>
                ) : (
                  <PositionRiskTable
                    items={items}
                    metric={metric}
                    onOpen={(p) => update({ position: p.position_id })}
                  />
                )}
              </Card>
              <Text size="xs" c="dimmed">
                Карта показывает, где сосредоточены условия для коррупции, и не является выводом о
                правонарушении. Решение о проверке принимает аналитик.
              </Text>
              <PositionRiskDrawer position={opened} onClose={() => update({ position: null })} />
            </Stack>
          );
        }}
      </QueryState>
    </>
  );
}
