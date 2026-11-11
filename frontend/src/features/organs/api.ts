import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/api';

export const organsKeys = { all: ['organs'] as const };

export const useOrgans = () =>
  useQuery({ queryKey: organsKeys.all, queryFn: api.organs.list, staleTime: Infinity });
