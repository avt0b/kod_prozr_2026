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
  AdminUser,
  AdminUserCreate,
  AdminUserUpdate,
  Appeal,
  AppealDetails,
  AppealsQuery,
  AssistantAnswer,
  CitizenAppeal,
  CreateAppealPayload,
  OfficialGraph,
  OfficialsQuery,
  Organ,
  Paginated,
  RecomputeResult,
  ReportDraft,
  RiskMap,
  RiskMapQuery,
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
    map: (query: RiskMapQuery = {}) =>
      request<RiskMap>('GET', '/risk-map', { query: { ...query } }),
  },

  appeals: {
    list: (query: AppealsQuery) =>
      request<Paginated<Appeal>>('GET', '/appeals', { query: { ...query } }),
    get: (id: UUID) => request<AppealDetails>('GET', `/appeals/${id}`),
    create: (payload: CreateAppealPayload) =>
      request<Appeal>('POST', '/appeals', { body: payload, timeoutMs: 150_000 }),
    reanalyze: (id: UUID) =>
      request<Appeal>('POST', `/appeals/${id}/reanalyze`, { timeoutMs: 150_000 }),
    /** Рассмотрение аналитиком: analyzed → routed, любой незакрытый → closed. */
    setStatus: (id: UUID, status: 'routed' | 'closed') =>
      request<Appeal>('POST', `/appeals/${id}/status`, { body: { status } }),
  },

  citizen: {
    appeals: (query: { limit?: number; offset?: number } = {}) =>
      request<Paginated<CitizenAppeal>>('GET', '/citizen/appeals', { query: { ...query } }),
    submit: (text: string) =>
      request<CitizenAppeal>('POST', '/citizen/appeals', { body: { text }, timeoutMs: 150_000 }),
  },

  admin: {
    users: (query: { role?: AdminUser['role']; query?: string; limit?: number } = {}) =>
      request<Paginated<AdminUser>>('GET', '/admin/users', { query: { ...query } }),
    create: (payload: AdminUserCreate) =>
      request<AdminUser>('POST', '/admin/users', { body: payload }),
    update: (id: UUID, payload: AdminUserUpdate) =>
      request<AdminUser>('PATCH', `/admin/users/${id}`, { body: payload }),
    remove: (id: UUID) => request<void>('DELETE', `/admin/users/${id}`),
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
