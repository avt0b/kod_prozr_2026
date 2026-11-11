import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type AppealsQuery, type CreateAppealPayload } from '@/shared/api';

export const appealsKeys = {
  all: ['appeals'] as const,
  list: (q: AppealsQuery) => ['appeals', 'list', q] as const,
  detail: (id: string) => ['appeals', 'detail', id] as const,
};

export const useAppeals = (q: AppealsQuery) =>
  useQuery({
    queryKey: appealsKeys.list(q),
    queryFn: () => api.appeals.list(q),
    placeholderData: keepPreviousData,
  });

export const useAppeal = (id: string) =>
  useQuery({ queryKey: appealsKeys.detail(id), queryFn: () => api.appeals.get(id) });

function useInvalidateAfterAppealChange() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: appealsKeys.all });
    void qc.invalidateQueries({ queryKey: ['stats'] });
    void qc.invalidateQueries({ queryKey: ['officials'] });
  };
}

export function useCreateAppeal() {
  const invalidate = useInvalidateAfterAppealChange();
  return useMutation({
    mutationFn: (payload: CreateAppealPayload) => api.appeals.create(payload),
    onSuccess: invalidate,
  });
}

export function useReanalyzeAppeal() {
  const invalidate = useInvalidateAfterAppealChange();
  return useMutation({
    mutationFn: (id: string) => api.appeals.reanalyze(id),
    onSuccess: invalidate,
  });
}
