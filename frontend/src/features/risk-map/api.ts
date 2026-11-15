import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api, type RiskMapQuery } from '@/shared/api';

/** Ключ под префиксом ['stats']: useRecomputeRisk сбрасывает его вместе со счётчиками. */
export const riskMapKeys = {
  map: (q: RiskMapQuery) => ['stats', 'risk-map', q] as const,
};

export const useRiskMap = (q: RiskMapQuery = {}) =>
  useQuery({
    queryKey: riskMapKeys.map(q),
    queryFn: () => api.risk.map(q),
    placeholderData: keepPreviousData,
  });
