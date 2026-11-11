import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/api';

export const statsKeys = {
  overview: ['stats', 'overview'] as const,
};

export const useOverview = () =>
  useQuery({ queryKey: statsKeys.overview, queryFn: api.stats.overview });

/** POST /risk/recompute — после пересчёта инвалидируем всё, что зависит от баллов. */
export function useRecomputeRisk() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.risk.recompute,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['stats'] });
      void qc.invalidateQueries({ queryKey: ['officials'] });
    },
  });
}
