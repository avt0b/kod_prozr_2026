import { readFileSync } from 'node:fs';
import { test as base, expect, type APIRequestContext } from '@playwright/test';

export function credentials(): { username: string; password: string } {
  if (process.env.E2E_USERNAME && process.env.E2E_PASSWORD)
    return { username: process.env.E2E_USERNAME, password: process.env.E2E_PASSWORD };
  return JSON.parse(
    readFileSync(new URL('../../.codex-build/local-auth.json', import.meta.url), 'utf8'),
  );
}
type Storage = Awaited<ReturnType<APIRequestContext['storageState']>>;
type WorkerSession = { token: string; storage: Storage };
export const test = base.extend<object, { workerSession: WorkerSession }>({
  workerSession: [
    async ({ playwright }, provide) => {
      const api = await playwright.request.newContext();
      const response = await api.post(
        `${process.env.API_URL ?? 'http://localhost:8000/api/v1'}/auth/login`,
        { data: credentials() },
      );
      expect(response.ok(), 'E2E user must be provisioned before test run').toBe(true);
      const body = await response.json();
      await provide({ token: body.access_token, storage: await api.storageState() });
      await api.dispose();
    },
    { scope: 'worker' },
  ],
  request: async ({ playwright, workerSession }, provide) => {
    const api = await playwright.request.newContext({
      extraHTTPHeaders: { Authorization: `Bearer ${workerSession.token}` },
    });
    await provide(api);
    await api.dispose();
  },
  page: async ({ page, workerSession }, provide) => {
    await page.context().addCookies(workerSession.storage.cookies);
    await provide(page);
    workerSession.storage = await page.context().storageState();
  },
});
export { expect };
export type { APIRequestContext, Locator, Page } from '@playwright/test';
