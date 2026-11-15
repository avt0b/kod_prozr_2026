/**
 * Скриншоты для слайдов со стенда по сценарию docs/demo.md (1920×1080).
 *
 *   BASE_URL=http://127.0.0.1:5173 node screenshots.mjs
 *
 * Нужен запущенный фронт, смотрящий в реальный API с сидами (не моки). Скрипт создаёт
 * демо-обращение H1 через форму, поэтому каждый запуск добавляет одно обращение:
 * снимайте на свежем стенде (`make reset && make seed`). Браузер: `npx playwright install chromium`.
 *
 * Полные кадры 1920×1080: overview, appeal, ranking, profile, graph, report. Фрагменты для
 * слайдов (обрезка по элементам страницы): appeal-main, ranking-top, profile-head, graph-card,
 * report-page. Кроме PNG пишет `screenshots/stand.json` — факты прогона (место и балл Соколова до и после
 * обращения, категория и движок разбора, флаги). build.mjs берёт подписи слайдов оттуда.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const base = (process.env.BASE_URL ?? 'http://127.0.0.1:5173').replace(/\/+$/, '');
const out = path.resolve(process.env.OUT_DIR ?? path.join(here, 'screenshots'));
const official = 'Соколов Андрей Викторович';
const r01 = 'Родственник — поставщик органа';

await fs.mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}),
});
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  locale: 'ru-RU',
  colorScheme: 'light',
});
// Служебные элементы не для слайдов: кнопка React Query Devtools (dev-сборка) и всплывающие уведомления.
await context.addInitScript(() => {
  const style = document.createElement('style');
  style.textContent =
    '.tsqd-parent-container, .mantine-Notifications-root { display: none !important; }';
  document.addEventListener('DOMContentLoaded', () => document.head.append(style));
});
const page = await context.newPage();
page.setDefaultTimeout(20_000);
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));

/** Дождаться, пока сеть и анимации успокоятся, затем снять видимую область. */
async function shot(name) {
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);
  const file = path.join(out, `${name}.png`);
  await page.screenshot({ path: file });
  console.log('saved', path.relative(process.cwd(), file));
}

/**
 * Фрагмент для слайда: прямоугольник в координатах страницы, охватывающий все элементы
 * `selector`, с отступом pad; высота ограничена maxHeight.
 */
async function crop(name, selector, { maxHeight = 1080, pad = 10 } = {}) {
  const clip = await page.evaluate(
    ({ selector, pad }) => {
      const rects = [...document.querySelectorAll(selector)]
        .map((el) => el.getBoundingClientRect())
        .filter((r) => r.width > 0 && r.height > 0);
      if (!rects.length) return null;
      const sx = window.scrollX;
      const sy = window.scrollY;
      const x = Math.max(0, Math.min(...rects.map((r) => r.left)) + sx - pad);
      const y = Math.max(0, Math.min(...rects.map((r) => r.top)) + sy - pad);
      const right = Math.max(...rects.map((r) => r.right)) + sx + pad;
      const bottom = Math.max(...rects.map((r) => r.bottom)) + sy + pad;
      return { x, y, width: right - x, height: bottom - y };
    },
    { selector, pad },
  );
  if (!clip) throw new Error(`Нет элементов для фрагмента ${name}: ${selector}`);
  clip.height = Math.min(clip.height, maxHeight);
  const file = path.join(out, `${name}.png`);
  await page.screenshot({ path: file, clip, fullPage: true });
  console.log('saved', path.relative(process.cwd(), file));
}

/** Место и балл служащего в видимой таблице рейтинга: первые две ячейки строки. */
async function rankOf(name) {
  const cells = page.getByRole('row').filter({ hasText: name }).first().getByRole('cell');
  const [rank, score] = await Promise.all([cells.nth(0).textContent(), cells.nth(1).textContent()]);
  return { rank: Number(rank), score: Number(score) };
}

const isApi = (response, method, pattern) =>
  response.request().method() === method && pattern.test(new URL(response.url()).pathname);

const stand = { taken_at: new Date().toISOString(), base_url: base, official };
try {
  // 1. Главная: счётчики, уровни и топ-10 до обращения.
  await page.goto(`${base}/`);
  await page.getByRole('cell', { name: official, exact: true }).waitFor();
  stand.before = await rankOf(official);
  await shot('overview');

  // 2. Новое обращение H1 (текст примера совпадает с docs/demo.md) и его разбор.
  await page.goto(`${base}/appeals/new`);
  await page.getByRole('button', { name: 'Вставить пример' }).click();
  const text = await page.getByLabel('Текст обращения').inputValue();
  if (!text.startsWith('Здравствуйте. Хочу сообщить')) throw new Error('Пример не совпадает с H1');
  const created = page.waitForResponse((r) => isApi(r, 'POST', /\/appeals$/), { timeout: 90_000 });
  await page.getByRole('button', { name: 'Отправить на анализ' }).click();
  const appeal = await (await created).json();
  await page.waitForURL(/\/appeals\/(?!new)[^/]+$/);
  await page.getByRole('link', { name: official }).first().waitFor();
  stand.appeal = {
    category: appeal.analysis?.category ?? null,
    engine: appeal.analysis?.engine ?? null,
    is_corruption: appeal.analysis?.is_corruption ?? null,
    linked: (appeal.linked_person_ids ?? []).length,
  };
  await shot('appeal');
  await crop('appeal-main', 'main > * > *');

  // 3. Рейтинг после обращения: Соколов поднимается наверх.
  await page.goto(`${base}/officials`);
  const row = page.getByRole('cell', { name: official, exact: true }).first();
  await row.waitFor();
  stand.after = await rankOf(official);
  await shot('ranking');
  await crop('ranking-top', 'table tr:nth-child(-n+5), table thead tr', { pad: 0 });

  // 4. Профиль Соколова: должность, полномочия, флаги.
  const flags = page.waitForResponse((r) => isApi(r, 'GET', /\/officials\/[^/]+\/flags$/));
  await row.click();
  await page.waitForURL(/\/officials\/[^/]+$/);
  stand.flags = [...new Set((await (await flags).json()).items.map((f) => f.rule_code))].sort();
  const graph = page.getByTestId('relation-graph');
  await graph.waitFor();
  await shot('profile');
  await crop('profile-head', 'main .mantine-Paper-root:has(h2)', { pad: 0 });

  // 5. Граф с подсвеченной цепочкой R01.
  await page.getByText(r01, { exact: true }).first().click();
  await page.getByText('подсвечена цепочка R01').waitFor();
  await page.getByRole('button', { name: 'Вписать граф' }).click();
  await graph.evaluate((el) => el.scrollIntoView({ block: 'center' }));
  await shot('graph');
  await crop('graph-card', 'main .mantine-Paper-root:has([data-testid="relation-graph"])', {
    pad: 0,
  });

  // 6. Черновик докладной.
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole('button', { name: 'Сформировать докладную' }).click();
  await page.waitForURL(/\/reports\//, { timeout: 90_000 });
  await page.getByText('Черновик', { exact: false }).first().waitFor();
  await shot('report');
  await crop('report-page', 'main > * > *', { maxHeight: 700 });

  if (errors.length) throw new Error(`Ошибки страницы: ${errors.join('; ')}`);
  if (stand.before.rank <= stand.after.rank && stand.before.score >= stand.after.score) {
    console.warn(
      'ВНИМАНИЕ: балл и место не изменились — стенд не свежий? Нужен make reset && make seed.',
    );
  }
  await fs.writeFile(path.join(out, 'stand.json'), `${JSON.stringify(stand, null, 2)}\n`);
  console.log(`Готово: 6 скриншотов, 5 фрагментов и stand.json в ${out}`);
  console.log(JSON.stringify(stand));
} finally {
  await browser.close();
}
