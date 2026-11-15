/**
 * Скриншоты для слайдов со стенда по сценарию docs/demo.md (1920×1080).
 *
 *   BASE_URL=http://127.0.0.1:5173 node screenshots.mjs
 *
 * Обычно запускается из reshoot.sh (свежая БД → съёмка → сборка). Нужен фронт, смотрящий в реальный
 * API с сидами (не моки). Скрипт создаёт демо-обращение H1 через форму, поэтому снимать нужно на
 * свежем стенде: если Соколов уже первый, скрипт останавливается (обойти: ALLOW_STALE=1).
 * Браузер: `npm run browsers --prefix docs/presentation`.
 *
 * Полные кадры 1920×1080: overview, appeal, ranking, profile, graph, report. Фрагменты для
 * слайдов (обрезка по элементам страницы): appeal-main, ranking-top, profile-head, graph-card,
 * report-page. Кроме PNG пишет `stand.json` — факты прогона (место и балл Соколова до и после
 * обращения, категория и движок разбора, флаги). build.mjs берёт подписи слайдов оттуда.
 *
 * Кадры сначала снимаются во временную папку и попадают в OUT_DIR только после успешного прохода
 * всего сценария: упавший прогон не оставляет смесь новых и старых файлов. При ошибке скрипт
 * пишет шаг, адрес страницы и сохраняет `failure.png` во временной папке.
 *
 * Переменные: BASE_URL, OUT_DIR (по умолчанию ./screenshots), BROWSER_CHANNEL, STEP_TIMEOUT_MS
 * (ожидание элементов, 30 000), ANALYSIS_TIMEOUT_MS (разбор обращения и докладная, 200 000:
 * с LLM бэкенд ждёт модель до 2×90 с), ALLOW_STALE=1 — снимать на несвежем стенде.
 */
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const base = (process.env.BASE_URL ?? 'http://127.0.0.1:5173').replace(/\/+$/, '');
const out = path.resolve(process.env.OUT_DIR ?? path.join(here, 'screenshots'));
const stepTimeout = Number(process.env.STEP_TIMEOUT_MS ?? 30_000);
const analysisTimeout = Number(process.env.ANALYSIS_TIMEOUT_MS ?? 200_000);
const allowStale = process.env.ALLOW_STALE === '1';
const official = 'Соколов Андрей Викторович';
const r01 = 'Родственник — поставщик органа';
const exampleStart = 'Здравствуйте. Хочу сообщить';

const stage = await fs.mkdtemp(path.join(os.tmpdir(), 'kodprozr-shots-'));
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
page.setDefaultTimeout(stepTimeout);
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));

const written = [];

/** Дождаться, пока сеть и анимации успокоятся, затем снять видимую область. */
async function shot(name) {
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(stage, `${name}.png`) });
  written.push(`${name}.png`);
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
  await page.screenshot({ path: path.join(stage, `${name}.png`), clip, fullPage: true });
  written.push(`${name}.png`);
}

/** Место и балл служащего в видимой таблице рейтинга: первые две ячейки строки. */
async function rankOf(name) {
  const cells = page.getByRole('row').filter({ hasText: name }).first().getByRole('cell');
  const [rank, score] = await Promise.all([cells.nth(0).textContent(), cells.nth(1).textContent()]);
  const result = { rank: Number(rank), score: Number(score) };
  if (!Number.isFinite(result.rank) || !Number.isFinite(result.score)) {
    throw new Error(`Не прочитать место и балл из строки рейтинга: «${rank}», «${score}»`);
  }
  return result;
}

const isApi = (response, method, pattern) =>
  response.request().method() === method && pattern.test(new URL(response.url()).pathname);

/** Шаг сценария: имя попадает в лог и в сообщение об ошибке. */
let current = 'запуск';
async function step(name, fn) {
  current = name;
  const started = Date.now();
  await fn();
  console.log(`✓ ${name} (${((Date.now() - started) / 1000).toFixed(1)} с)`);
}

const stand = { taken_at: new Date().toISOString(), base_url: base, official };
let ok = false;
try {
  await step('главная: рейтинг до обращения', async () => {
    const response = await page.goto(`${base}/`);
    if (!response?.ok()) throw new Error(`Фронт ${base} ответил ${response?.status()}`);
    await page.getByText('Рабочее место аналитика').waitFor();
    if (await page.getByText('моки', { exact: true }).count()) {
      throw new Error('Фронт работает на моках (VITE_USE_MOCKS=true), нужен реальный API');
    }
    await page.getByRole('cell', { name: official, exact: true }).waitFor();
    stand.before = await rankOf(official);
    if (stand.before.rank === 1 && !allowStale) {
      throw new Error(
        `Соколов уже на 1-м месте (балл ${stand.before.score}): стенд не свежий, демо-обращение ` +
          'уже отправляли. Пересоздайте БД (reshoot.sh) или задайте ALLOW_STALE=1.',
      );
    }
    await shot('overview');
  });

  await step('новое обращение H1 и его разбор', async () => {
    await page.goto(`${base}/appeals/new`);
    await page.getByRole('button', { name: 'Вставить пример' }).click();
    const textarea = page.getByLabel('Текст обращения');
    // Значение поля обновляется после клика не мгновенно: ждём текст примера, а не читаем сразу.
    await page.waitForFunction(
      ({ el, start }) => el.value.startsWith(start),
      { el: await textarea.elementHandle(), start: exampleStart },
      { timeout: stepTimeout },
    );
    const created = page.waitForResponse((r) => isApi(r, 'POST', /\/appeals$/), {
      timeout: analysisTimeout,
    });
    await page.getByRole('button', { name: 'Отправить на анализ' }).click();
    const response = await created;
    if (!response.ok()) {
      throw new Error(`POST /appeals: ${response.status()} ${await response.text()}`);
    }
    const appeal = await response.json();
    stand.appeal = {
      category: appeal.analysis?.category ?? null,
      engine: appeal.analysis?.engine ?? null,
      is_corruption: appeal.analysis?.is_corruption ?? null,
      linked: (appeal.linked_person_ids ?? []).length,
    };
    await page.waitForURL(/\/appeals\/(?!new)[^/]+$/);
    await page
      .getByText(/^Разбор: /)
      .first()
      .waitFor();
    if (stand.appeal.linked) {
      await page.getByRole('link', { name: official }).first().waitFor();
    } else {
      console.warn('ВНИМАНИЕ: обращение не привязано ни к одному служащему.');
    }
    await shot('appeal');
    await crop('appeal-main', 'main > * > *');
  });

  let row;
  await step('рейтинг после обращения', async () => {
    await page.goto(`${base}/officials`);
    row = page.getByRole('cell', { name: official, exact: true }).first();
    await row.waitFor();
    stand.after = await rankOf(official);
    await shot('ranking');
    await crop('ranking-top', 'table tr:nth-child(-n+5), table thead tr', { pad: 0 });
  });

  let graph;
  await step('профиль Соколова', async () => {
    const flags = page.waitForResponse((r) => isApi(r, 'GET', /\/officials\/[^/]+\/flags$/));
    await row.click();
    await page.waitForURL(/\/officials\/[^/]+$/);
    stand.flags = [...new Set((await (await flags).json()).items.map((f) => f.rule_code))].sort();
    graph = page.getByTestId('relation-graph');
    await graph.waitFor();
    await shot('profile');
    await crop('profile-head', 'main .mantine-Paper-root:has(h2)', { pad: 0 });
  });

  await step('граф с цепочкой R01', async () => {
    await page.getByText(r01, { exact: true }).first().click();
    await page.getByText('подсвечена цепочка R01').waitFor();
    await page.getByRole('button', { name: 'Вписать граф' }).click();
    await graph.evaluate((el) => el.scrollIntoView({ block: 'center' }));
    await shot('graph');
    await crop('graph-card', 'main .mantine-Paper-root:has([data-testid="relation-graph"])', {
      pad: 0,
    });
  });

  await step('черновик докладной', async () => {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.getByRole('button', { name: 'Сформировать докладную' }).click();
    await page.waitForURL(/\/reports\//, { timeout: analysisTimeout });
    await page.getByText('Черновик', { exact: false }).first().waitFor();
    await shot('report');
    await crop('report-page', 'main > * > *', { maxHeight: 700 });
  });

  current = 'проверка результата';
  if (errors.length) throw new Error(`Ошибки страницы: ${errors.join('; ')}`);
  if (stand.after.rank >= stand.before.rank && stand.after.score <= stand.before.score) {
    console.warn('ВНИМАНИЕ: балл и место не изменились — стенд не свежий?');
  }
  await fs.writeFile(path.join(stage, 'stand.json'), `${JSON.stringify(stand, null, 2)}\n`);
  written.push('stand.json');
  ok = true;
} catch (error) {
  console.error(`\nОШИБКА на шаге «${current}» (${page.url()}):\n${error.message}`);
  await page
    .screenshot({ path: path.join(stage, 'failure.png') })
    .then(() => console.error(`Кадр ошибки и снятое до неё: ${stage}`))
    .catch(() => {});
  console.error(`Папка ${out} не изменена.`);
  process.exitCode = 1;
} finally {
  await browser.close();
}

if (ok) {
  await fs.mkdir(out, { recursive: true });
  for (const name of written) await fs.copyFile(path.join(stage, name), path.join(out, name));
  await fs.rm(stage, { recursive: true, force: true });
  console.log(`Готово: ${written.length - 1} PNG и stand.json в ${out}`);
  console.log(JSON.stringify(stand));
}
