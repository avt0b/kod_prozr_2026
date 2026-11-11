import { Card, Group, Pagination, Stack, Text } from '@mantine/core';
import { useSearchParams } from 'react-router';
import {
  OfficialsFilters,
  type OfficialsFilterValues,
} from '@/features/officials/OfficialsFilters';
import { OfficialsTable } from '@/features/officials/OfficialsTable';
import { useOfficials } from '@/features/officials/api';
import type { OfficialsSort } from '@/shared/api';
import { PageHeader, QueryState } from '@/shared/ui';

const PAGE_SIZE = 20;

/** Фильтры, сортировка и страница хранятся в URL — ссылку на выборку можно отправить коллеге. */
export function OfficialsPage() {
  const [params, setParams] = useSearchParams();
  const filters: OfficialsFilterValues = {
    query: params.get('query') ?? '',
    organId: params.get('organ_id'),
    minScore: params.get('min_score') ? Number(params.get('min_score')) : null,
  };
  const sort = (params.get('sort') as OfficialsSort | null) ?? '-risk_score';
  const page = Number(params.get('page') ?? 1);

  const update = (patch: Record<string, string | number | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v === null || v === '') next.delete(k);
      else next.set(k, String(v));
    }
    setParams(next, { replace: true });
  };

  const officials = useOfficials({
    query: filters.query || undefined,
    organ_id: filters.organId ?? undefined,
    min_score: filters.minScore ?? undefined,
    sort,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  return (
    <>
      <PageHeader
        title="Рейтинг служащих"
        description="Служащие, отсортированные по интегральному баллу коррупционного риска"
      />
      <Stack>
        <OfficialsFilters
          value={filters}
          onChange={(v) =>
            update({ query: v.query, organ_id: v.organId, min_score: v.minScore, page: null })
          }
        />
        <Card p={0}>
          <QueryState
            query={officials}
            isEmpty={(d) => d.items.length === 0}
            empty="По заданным фильтрам служащих не найдено"
          >
            {(data) => (
              <>
                <OfficialsTable
                  items={data.items}
                  sort={sort}
                  onSortChange={(s) => update({ sort: s, page: null })}
                  startIndex={(page - 1) * PAGE_SIZE}
                />
                <Group justify="space-between" p="md">
                  <Text size="sm" c="dimmed">
                    Найдено: {data.total}
                  </Text>
                  <Pagination
                    total={Math.ceil(data.total / PAGE_SIZE)}
                    value={page}
                    onChange={(p) => update({ page: p })}
                    size="sm"
                  />
                </Group>
              </>
            )}
          </QueryState>
        </Card>
      </Stack>
    </>
  );
}
