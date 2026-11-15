import { defineConfig } from '@playwright/test';

/**
 * E2E-прогон сценария демо (docs/demo.md) на уже запущенном стенде: фронт + реальный бэк без моков.
 * Переменные окружения:
 *   BASE_URL     — адрес фронта (по умолчанию http://localhost:5173);
 *   API_URL      — адрес API, на который смотрит фронт (по умолчанию http://localhost:8000/api/v1);
 *   DEMO_VIDEO=1 — записывать видео прогона 1920×1080 (для видео-бэкапа демо);
 *   DEMO_SLOWMO  — задержка между действиями браузера, мс (чтобы видео было читаемым);
 *   PW_CHANNEL   — канал браузера (`chrome`, `msedge`), если не установлен chromium Playwright.
 */
const video = process.env.DEMO_VIDEO === '1';
const slowMo = Number(process.env.DEMO_SLOWMO ?? 0);
const viewport = { width: 1920, height: 1080 };

export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/test-results',
  // Сценарий один и идёт по шагам демо, LLM может отвечать до минуты
  timeout: 5 * 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: [['list'], ['html', { outputFolder: './e2e/playwright-report', open: 'never' }]],
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:5173',
    browserName: 'chromium',
    ...(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {}),
    viewport,
    deviceScaleFactor: 1,
    locale: 'ru-RU',
    timezoneId: 'Europe/Moscow',
    colorScheme: 'light',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: video ? { mode: 'on', size: viewport } : 'off',
    launchOptions: slowMo > 0 ? { slowMo } : {},
  },
});
