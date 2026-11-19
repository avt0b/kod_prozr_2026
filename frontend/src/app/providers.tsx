import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import type { ReactNode } from 'react';
import { ApiError } from '@/shared/api';
import { theme, workspaceVariables } from './theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // 4xx (служащий не найден, неверный id) повтор не исправит: показываем ошибку сразу
      retry: (failures, error) =>
        failures < 1 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
      refetchOnWindowFocus: false,
    },
  },
});

export function Providers({ children }: { children: ReactNode }) {
  return (
    <MantineProvider
      theme={theme}
      cssVariablesResolver={workspaceVariables}
      defaultColorScheme="light"
    >
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
        {children}
        {import.meta.env.DEV && import.meta.env.VITE_QUERY_DEVTOOLS === 'true' && (
          <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
        )}
      </QueryClientProvider>
    </MantineProvider>
  );
}
