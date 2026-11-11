import { env } from '@/shared/config/env';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
export type QueryParams = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  query?: QueryParams;
  body?: unknown;
  signal?: AbortSignal;
  timeoutMs?: number;
}

/** Ошибка API. Формат тела ошибки бэка — см. docs/backend.md; поддерживаем {detail} и {error:{message}}. */
export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(status: number, message: string, payload?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

/** Удаляет пустые значения, чтобы не слать `?query=&organ_id=`. */
export function cleanQuery(query: QueryParams = {}): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue;
    out[key] = String(value);
  }
  return out;
}

function extractMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object') {
    const p = payload as { detail?: unknown; error?: { message?: unknown }; message?: unknown };
    if (typeof p.detail === 'string') return p.detail;
    if (typeof p.error?.message === 'string') return p.error.message;
    if (typeof p.message === 'string') return p.message;
  }
  return fallback;
}

async function httpRequest<T>(method: HttpMethod, path: string, opts: RequestOptions): Promise<T> {
  const params = new URLSearchParams(cleanQuery(opts.query));
  const qs = params.toString();
  const url = `${env.apiUrl}${path}${qs ? `?${qs}` : ''}`;

  const res = await fetch(url, {
    method,
    signal: opts.timeoutMs
      ? AbortSignal.any([
          AbortSignal.timeout(opts.timeoutMs),
          ...(opts.signal ? [opts.signal] : []),
        ])
      : opts.signal,
    headers: {
      Accept: 'application/json',
      ...(opts.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });

  const text = await res.text();
  let payload: unknown = undefined;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, extractMessage(payload, `Ошибка ${res.status}`), payload);
  }
  return payload as T;
}

/**
 * Единая точка всех запросов. При VITE_USE_MOCKS=true запрос уходит в in-memory моки
 * (src/shared/api/mocks), модуль моков грузится лениво и не попадает в основной чанк.
 */
export async function request<T>(
  method: HttpMethod,
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  if (env.useMocks) {
    const { mockRequest } = await import('./mocks');
    return mockRequest<T>(method, path, opts);
  }
  try {
    return await httpRequest<T>(method, path, opts);
  } catch (error) {
    if (error instanceof Error && error.name === 'TimeoutError') {
      throw new ApiError(
        408,
        'Время ожидания анализа истекло. Проверьте список обращений перед повторной отправкой: сервер мог сохранить обращение.',
      );
    }
    throw error;
  }
}
