/**
 * Типизированные функции эндпоинтов по docs/contracts.md (раздел API).
 * Одна функция = один эндпоинт. Хуки TanStack Query живут в src/features/<фича>/api.ts.
 */
import { request } from './client';
import type {
  Appeal,
  AppealDetails,
  AppealsQuery,
  AssistantAnswer,
  CreateAppealPayload,
  OfficialGraph,
  OfficialListItem,
  OfficialProfile,
  OfficialsQuery,
  Organ,
  Paginated,
  RecomputeResult,
  ReportDraft,
  RiskFlag,
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
    list: (query: OfficialsQuery) =>
      request<Paginated<OfficialListItem>>('GET', '/officials', { query: { ...query } }),
    get: (id: UUID) => request<OfficialProfile>('GET', `/officials/${id}`),
    graph: (id: UUID, depth = 2) =>
      request<OfficialGraph>('GET', `/officials/${id}/graph`, { query: { depth } }),
    flags: (id: UUID) => request<Paginated<RiskFlag>>('GET', `/officials/${id}/flags`),
  },

  risk: {
    recompute: () => request<RecomputeResult>('POST', '/risk/recompute'),
  },

  appeals: {
    list: (query: AppealsQuery) =>
      request<Paginated<Appeal>>('GET', '/appeals', { query: { ...query } }),
    get: (id: UUID) => request<AppealDetails>('GET', `/appeals/${id}`),
    create: (payload: CreateAppealPayload) =>
      request<Appeal>('POST', '/appeals', { body: payload }),
    reanalyze: (id: UUID) => request<Appeal>('POST', `/appeals/${id}/reanalyze`),
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
