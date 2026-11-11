/**
 * Типизированные функции эндпоинтов по docs/contracts.md (раздел API).
 * Одна функция = один эндпоинт. Хуки TanStack Query живут в src/features/<фича>/api.ts.
 */
import { request } from './client';
import {
  normalizeFlag,
  normalizeOfficial,
  normalizeProfile,
  type WireFlag,
  type WireListItem,
  type WireProfile,
} from './officialAdapters';
import type {
  Appeal,
  AppealDetails,
  AppealsQuery,
  AssistantAnswer,
  CreateAppealPayload,
  OfficialGraph,
  OfficialsQuery,
  Organ,
  Paginated,
  RecomputeResult,
  ReportDraft,
  StatsOverview,
  UUID,
} from './types';

export const api = {
  stats: {
    overview: () => request<StatsOverview>('GET', '/stats/overview'),
  },

  organs: {
    list: () => request<Paginated<Organ>>('GET', '/organs'),
  },

  officials: {
    list: async (query: OfficialsQuery) => {
      const result = await request<Paginated<WireListItem>>('GET', '/officials', {
        query: { ...query },
      });
      return { ...result, items: result.items.map(normalizeOfficial) };
    },
    get: async (id: UUID) => {
      const [profile, flags] = await Promise.all([
        request<WireProfile>('GET', `/officials/${id}`),
        request<Paginated<WireFlag>>('GET', `/officials/${id}/flags`),
      ]);
      return normalizeProfile(profile, flags.items);
    },
    graph: (id: UUID, depth = 2) =>
      request<OfficialGraph>('GET', `/officials/${id}/graph`, { query: { depth } }),
    flags: async (id: UUID) => {
      const result = await request<Paginated<WireFlag>>('GET', `/officials/${id}/flags`);
      return { ...result, items: result.items.map(normalizeFlag) };
    },
  },

  risk: {
    recompute: () => request<RecomputeResult>('POST', '/risk/recompute'),
  },

  appeals: {
    list: (query: AppealsQuery) =>
      request<Paginated<Appeal>>('GET', '/appeals', { query: { ...query } }),
    get: (id: UUID) => request<AppealDetails>('GET', `/appeals/${id}`),
    create: (payload: CreateAppealPayload) =>
      request<Appeal>('POST', '/appeals', { body: payload, timeoutMs: 150_000 }),
    reanalyze: (id: UUID) =>
      request<Appeal>('POST', `/appeals/${id}/reanalyze`, { timeoutMs: 150_000 }),
  },

  reports: {
    create: (personId: UUID) =>
      request<ReportDraft>('POST', '/reports', { body: { person_id: personId } }),
    get: (id: UUID) => request<ReportDraft>('GET', `/reports/${id}`),
  },

  assistant: {
    ask: (question: string) =>
      request<AssistantAnswer>('POST', '/assistant/ask', { body: { question } }),
  },
};
