/** Все переменные окружения фронта читаются только здесь. */
export const env = {
  apiUrl: (import.meta.env.VITE_API_URL ?? '/api/v1').replace(/\/+$/, ''),
  useMocks: import.meta.env.VITE_USE_MOCKS === 'true',
  mockDelayMs: Number(import.meta.env.VITE_MOCK_DELAY_MS ?? 300),
} as const;
