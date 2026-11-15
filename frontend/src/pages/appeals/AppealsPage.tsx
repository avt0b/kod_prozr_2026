import { Button, Card, Group, Pagination, Stack, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { Link, useSearchParams } from 'react-router';
import { AppealFilters } from '@/features/appeals/AppealFilters';
import { AppealsTable } from '@/features/appeals/AppealsTable';
import { useAppeals } from '@/features/appeals/api';
import type { AppealCategory, AppealStatus } from '@/shared/api';
import { routes } from '@/shared/config/routes';
import { PageHeader, QueryState } from '@/shared/ui';
import { APPEAL_CATEGORY_LABELS, APPEAL_STATUS_LABELS } from '@/shared/lib/labels';

const PAGE_SIZE = 20;

export function AppealsPage() {
  const [params, setParams] = useSearchParams();
  const rawStatus = params.get('status');
  const rawCategory = params.get('category');
  const status =
    rawStatus && Object.hasOwn(APPEAL_STATUS_LABELS, rawStatus)
      ? (rawStatus as AppealStatus)
      : null;
  const category =
    rawCategory && Object.hasOwn(APPEAL_CATEGORY_LABELS, rawCategory)
      ? (rawCategory as AppealCategory)
      : null;
  const rawPage = Number(params.get('page') ?? 1);
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 && rawPage <= 1_000_000 ? rawPage : 1;

  const appeals = useAppeals({
    status: status ?? undefined,
    category: category ?? undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  const update = (patch: Record<string, string | number | null>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v === null || v === '') next.delete(k);
      else next.set(k, String(v));
    }
    setParams(next, { replace: true });
  };

  return (
    <>
      <PageHeader
        title="Обращения граждан"
        description="Входящие сообщения с автоматической классификацией и маршрутизацией"
        actions={
          <Button component={Link} to={routes.appealNew()} leftSection={<IconPlus size={16} />}>
            Новое обращение
          </Button>
        }
      />
      <Stack>
        <AppealFilters
          value={{ status, category }}
          onChange={(v) => update({ status: v.status, category: v.category, page: null })}
        />
        <Card p={0}>
          <QueryState query={appeals} isEmpty={(d) => d.items.length === 0} empty="Обращений нет">
            {(data) => (
              <>
                <AppealsTable items={data.items} />
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
