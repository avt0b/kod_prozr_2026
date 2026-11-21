import { env } from '@/shared/config/env';

export interface AuthUser {
  id: string;
  username: string;
}
interface Session {
  access_token: string;
  user: AuthUser;
  session_id: string;
}
let session: Session | null = null;
let ready = false;
let refreshing: Promise<boolean> | null = null;
const listeners = new Set<() => void>();
let snapshot = { user: null as AuthUser | null, ready: false, principal: '' };
export const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};
export const getSnapshot = () => snapshot;
export const accessToken = () => session?.access_token;
function update(value: Session | null) {
  session = value;
  ready = true;
  snapshot = {
    user: value?.user ?? null,
    ready,
    principal: value ? `${value.user.id}:${value.session_id}` : '',
  };
  listeners.forEach((listener) => listener());
}
async function authRequest(path: string, body?: unknown): Promise<Response> {
  return fetch(`${env.apiUrl}/auth/${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(path === 'logout' && session ? { Authorization: `Bearer ${session.access_token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
export function refreshSession(): Promise<boolean> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    try {
      const response = await authRequest('refresh');
      if (!response.ok) {
        update(null);
        return false;
      }
      update((await response.json()) as Session);
      return true;
    } catch {
      update(null);
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}
export async function login(username: string, password: string): Promise<void> {
  if (refreshing) await refreshing;
  const response = await authRequest('login', { username, password });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(
      typeof payload?.detail === 'string'
        ? payload.detail
        : 'Не удалось войти. Проверьте соединение.',
    );
  }
  update((await response.json()) as Session);
}
export async function logout(): Promise<void> {
  if (refreshing) await refreshing;
  const response = await authRequest('logout');
  if (!response.ok) throw new Error('Не удалось завершить сессию. Повторите выход.');
  update(null);
}
