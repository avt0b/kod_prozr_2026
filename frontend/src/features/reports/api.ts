import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/api';

export const reportsKeys = {
  detail: (id: string) => ['reports', 'detail', id] as const,
};

export const useReport = (id: string) =>
  useQuery({ queryKey: reportsKeys.detail(id), queryFn: () => api.reports.get(id) });

export function useCreateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (personId: string) => api.reports.create(personId),
    // Кладём созданный черновик в кеш, чтобы страница докладной открылась без лишнего запроса
    onSuccess: (report) => qc.setQueryData(reportsKeys.detail(report.id), report),
  });
}
