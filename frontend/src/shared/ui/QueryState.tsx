import { Alert, Button, Center, Loader, Stack, Text } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import type { ReactNode } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';

interface Props<T> {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
  /** Что показать, если данные пустые (по умолчанию ничего не проверяем). */
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
}

/** Единообразная обработка loading / error / empty для useQuery. */
export function QueryState<T>({ query, children, isEmpty, empty }: Props<T>) {
  if (query.isPending) {
    return (
      <Center
        py="xl"
        className="workspace-surface workspace-state"
        role="status"
        aria-label="Загрузка данных"
      >
        <Loader />
      </Center>
    );
  }
  if (query.isError) {
    return (
      <Alert color="red" icon={<IconAlertTriangle size={18} />} title="Не удалось загрузить данные">
        <Stack gap="xs" align="flex-start">
          <Text size="sm">
            {query.error instanceof Error ? query.error.message : String(query.error)}
          </Text>
          <Button size="xs" variant="light" color="red" onClick={() => query.refetch()}>
            Повторить
          </Button>
        </Stack>
      </Alert>
    );
  }
  if (isEmpty?.(query.data)) {
    return (
      <Center py="xl" className="workspace-surface workspace-state">
        <Text c="dimmed">{empty ?? 'Ничего не найдено'}</Text>
      </Center>
    );
  }
  return <>{children(query.data)}</>;
}
