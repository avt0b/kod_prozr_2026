import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api, type OfficialsQuery } from '@/shared/api';

export const officialsKeys = {
  all: ['officials'] as const,
  list: (q: OfficialsQuery) => ['officials', 'list', q] as const,
  detail: (id: string) => ['officials', 'detail', id] as const,
  graph: (id: string, depth: number) => ['officials', 'graph', id, depth] as const,
};

export const useOfficials = (q: OfficialsQuery) =>
  useQuery({
    queryKey: officialsKeys.list(q),
    queryFn: () => api.officials.list(q),
    placeholderData: keepPreviousData,
  });

export const useOfficial = (id: string) =>
  useQuery({ queryKey: officialsKeys.detail(id), queryFn: () => api.officials.get(id) });

export const useOfficialGraph = (id: string, depth = 2) =>
  useQuery({
    queryKey: officialsKeys.graph(id, depth),
    queryFn: () => api.officials.graph(id, depth),
  });
