/**
 * Мок-сервер: перехватывает request() при VITE_USE_MOCKS=true.
 * Чтобы добавить эндпоинт — добавьте строку в routes (метод, шаблон пути, обработчик).
 */
import { env } from '@/shared/config/env';
import { ApiError, type HttpMethod, type RequestOptions } from '../client';
import type { AppealsQuery, CreateAppealPayload, OfficialsQuery } from '../types';
import * as db from './db';
import { organs } from './seed';

type Handler = (params: Record<string, string>, opts: RequestOptions) => unknown;

interface Route {
  method: HttpMethod;
  pattern: RegExp;
  handler: Handler;
}

const notFound = (what: string): never => {
  throw new ApiError(404, `${what} не найден(о)`, { detail: `${what} не найден(о)` });
};

/** '/officials/:id/graph' → RegExp с именованными группами. */
const path = (template: string) => new RegExp(`^${template.replace(/:(\w+)/g, '(?<$1>[^/]+)')}$`);

const routes: Route[] = [
  { method: 'GET', pattern: path('/stats/overview'), handler: () => db.statsOverview() },
  {
    method: 'GET',
    pattern: path('/organs'),
    handler: () => ({ items: organs, total: organs.length }),
  },

  {
    method: 'GET',
    pattern: path('/officials'),
    handler: (_, { query }) => db.listOfficials((query ?? {}) as OfficialsQuery),
  },
  {
    method: 'GET',
    pattern: path('/officials/:id'),
    handler: ({ id }) => db.officialProfile(id) ?? notFound('Служащий'),
  },
  {
    method: 'GET',
    pattern: path('/officials/:id/graph'),
    handler: ({ id }, { query }) =>
      db.officialGraph(id, Number(query?.depth ?? 2)) ?? notFound('Служащий'),
  },
  {
    method: 'GET',
    pattern: path('/officials/:id/flags'),
    handler: ({ id }) => {
      const items = db.flagsOf(id);
      return { items, total: items.length };
    },
  },
  { method: 'POST', pattern: path('/risk/recompute'), handler: () => db.recompute() },

  {
    method: 'GET',
    pattern: path('/appeals'),
    handler: (_, { query }) => {
      const q = (query ?? {}) as AppealsQuery;
      let items = [...db.state.appeals].sort((a, b) => b.received_at.localeCompare(a.received_at));
      if (q.status) items = items.filter((a) => a.status === q.status);
      if (q.category) items = items.filter((a) => a.analysis?.category === q.category);
      const offset = Number(q.offset ?? 0);
      const limit = Number(q.limit ?? 20);
      return { items: items.slice(offset, offset + limit), total: items.length };
    },
  },
  {
    method: 'POST',
    pattern: path('/appeals'),
    handler: (_, { body }) => {
      const payload = body as CreateAppealPayload;
      if (!payload?.text?.trim()) {
        throw new ApiError(422, 'Текст обращения не может быть пустым');
      }
      return db.createAppeal(payload.text.trim(), payload.channel);
    },
  },
  {
    method: 'GET',
    pattern: path('/appeals/:id'),
    handler: ({ id }) => db.appealDetails(id) ?? notFound('Обращение'),
  },
  {
    method: 'POST',
    pattern: path('/appeals/:id/reanalyze'),
    handler: ({ id }) => db.reanalyzeAppeal(id) ?? notFound('Обращение'),
  },

  {
    method: 'POST',
    pattern: path('/reports'),
    handler: (_, { body }) =>
      db.createReport((body as { person_id: string }).person_id) ?? notFound('Служащий'),
  },
  {
    method: 'GET',
    pattern: path('/reports/:id'),
    handler: ({ id }) => db.state.reports.find((r) => r.id === id) ?? notFound('Черновик'),
  },

  {
    method: 'POST',
    pattern: path('/assistant/ask'),
    handler: (_, { body }) => db.assistantAnswer((body as { question: string }).question ?? ''),
  },
];

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function mockRequest<T>(
  method: HttpMethod,
  urlPath: string,
  opts: RequestOptions,
): Promise<T> {
  await sleep(env.mockDelayMs);
  for (const route of routes) {
    if (route.method !== method) continue;
    const match = route.pattern.exec(urlPath);
    if (!match) continue;
    const result = route.handler(match.groups ?? {}, opts);
    if (import.meta.env.DEV) {
      console.debug(`[mock] ${method} ${urlPath}`, opts.query ?? opts.body ?? '', result);
    }
    // structuredClone — чтобы компоненты не могли случайно мутировать «базу»
    return structuredClone(result) as T;
  }
  throw new ApiError(404, `[mock] Нет обработчика для ${method} ${urlPath}`);
}
