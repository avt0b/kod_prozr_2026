import { readFileSync } from 'node:fs';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';

/**
 * Сценарий демо из docs/demo.md на реальном стенде (без моков), 1920×1080.
 * Баллы не хардкодим: веса правил меняются, проверяем место в рейтинге и рост балла.
 * Сценарий создаёт демо-обращение и докладную — запускать на демо-стенде после `make reset && make seed`
 * (или на отдельной БД). На повторном прогоне Соколов уже первый, тогда рост балла не обязателен.
 */

const API = (process.env.API_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');
const HERE = dirname(fileURLToPath(import.meta.url));
const SHOTS = join(HERE, 'screenshots');
const DEMO_TEXT = readFileSync(join(HERE, '../../demo/appeal_h1.txt'), 'utf8').trim();
const SOKOLOV = 'Соколов Андрей Викторович';
const N1 = 'Орлов Сергей Михайлович';
const ASSISTANT_QUESTION = 'Покажи служащих, у которых родственники среди подрядчиков их органа';
/** Кейсы C2–C5 из docs/demo.md: правило → служащий, который в фильтре по правилу в первой тройке. */
const RULE_CASES = [
  { rule: 'R02', name: 'Лебедева Ольга Николаевна' },
  { rule: 'R03', name: 'Гусев Павел Сергеевич' },
  { rule: 'R04', name: 'Морозов Денис Игоревич' },
  { rule: 'R05', name: 'Белова Ирина Андреевна' },
] as const;

interface ListItem {
  id: string;
  full_name: string;
  risk_score: number;
  top_flags: { rule_code: string }[];
}
interface Standing {
  id: string;
  score: number;
  rank: number;
}

async function apiGet<T>(request: APIRequestContext, path: string): Promise<T> {
  const res = await request.get(`${API}${path}`);
  expect(res.status(), `GET ${path}`).toBe(200);
  return (await res.json()) as T;
}

/** Место и балл служащего в рейтинге по умолчанию (`-risk_score`). */
async function standing(request: APIRequestContext, fullName: string): Promise<Standing> {
  const data = await apiGet<{ items: ListItem[] }>(
    request,
    '/officials?sort=-risk_score&limit=100&offset=0',
  );
  const index = data.items.findIndex((i) => i.full_name === fullName);
  expect(index, `${fullName} есть в топ-100`).toBeGreaterThanOrEqual(0);
  return { id: data.items[index].id, score: data.items[index].risk_score, rank: index + 1 };
}

/** Пометка в отчёте Playwright и в выводе прогона: места и баллы, расхождения с docs/demo.md. */
function note(annotation: { type: string; description: string }) {
  test.info().annotations.push(annotation);
  console.debug(`[demo] ${annotation.type}: ${annotation.description}`);
}

/** Ждём, пока догрузятся все запросы экрана: в SPA `networkidle` после перехода не срабатывает. */
async function settle(page: Page) {
  await expect(page.locator('.mantine-Loader-root, .mantine-Skeleton-root')).toHaveCount(0);
  // Анимации Mantine (выпадающие списки, переходы) — 150–200 мс
  await page.waitForTimeout(300);
}

async function shot(page: Page, name: string, fullPage = false) {
  await settle(page);
  await page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage });
}

/** На 1920×1080 у страницы не должно быть горизонтальной прокрутки. */
async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, 'горизонтальная прокрутка страницы').toBeLessThanOrEqual(0);
}

function tableRows(scope: Page | Locator) {
  return scope.locator('table tbody tr');
}

/** Состояние графа Cytoscape: подсвеченные узлы и координаты узла на экране. */
async function graphState(graph: Locator) {
  return graph.evaluate((el) => {
    const cy = (el as unknown as { _cyreg: { cy: CyLike } })._cyreg.cy;
    return {
      nodes: cy.nodes().map((n) => ({ id: n.id(), type: n.data('type') as string })),
      highlighted: cy.nodes('.hl').map((n) => n.id()),
      highlightedLabels: cy.nodes('.hl').map((n) => n.data('label') as string),
      highlightedEdges: cy.edges('.hl').length,
      faded: cy.nodes('.faded').length,
    };
  });
}

async function clickGraphNode(page: Page, graph: Locator, nodeId: string) {
  const pos = await graph.evaluate((el, id) => {
    const cy = (el as unknown as { _cyreg: { cy: CyLike } })._cyreg.cy;
    const node = cy.getElementById(id);
    return node.renderedPosition();
  }, nodeId);
  const box = await graph.boundingBox();
  if (!box) throw new Error('граф не отрисован');
  await page.mouse.click(box.x + pos.x, box.y + pos.y);
}

/** Минимальный тип инстанса Cytoscape, достаточный для проверок (тип пакета в e2e не тянем). */
interface CyNode {
  id(): string;
  data(key: string): unknown;
  renderedPosition(): { x: number; y: number };
}
interface CyCollection {
  map<T>(fn: (n: CyNode) => T): T[];
  length: number;
}
interface CyLike {
  nodes(selector?: string): CyCollection;
  edges(selector?: string): CyCollection;
  getElementById(id: string): CyNode;
}

test('сценарий демо docs/demo.md проходит на реальном стенде', async ({ page, request }) => {
  mkdirSync(SHOTS, { recursive: true });

  // Ошибки в консоли, необработанные исключения и любые 4xx/5xx роняют прогон в конце
  const problems: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') problems.push(`console.error: ${msg.text()}`);
  });
  page.on('pageerror', (err) => problems.push(`pageerror: ${err.message}`));
  page.on('response', (res) => {
    if (res.status() >= 400)
      problems.push(`HTTP ${res.status()} ${res.request().method()} ${res.url()}`);
  });
  page.on('requestfailed', (req) =>
    problems.push(`request failed: ${req.method()} ${req.url()} ${req.failure()?.errorText}`),
  );

  const health = await request.get(API.replace(/\/api\/v1$/, '/health'));
  expect(health.ok(), 'бэк отвечает на /health').toBe(true);

  const before = await standing(request, SOKOLOV);
  note({
    type: 'Соколов до обращения',
    description: `${before.rank}-е место, балл ${before.score}`,
  });
  if (before.rank === 1)
    note({
      type: 'warning',
      description: 'Соколов уже первый: стенд не после make reset, рост балла проверяется мягко',
    });
  else expect(before.rank, 'до обращения Соколов на 2–5 месте').toBeLessThanOrEqual(5);

  let appealId = '';

  await test.step('0:30 Главная: счётчики и топ-10', async () => {
    const stats = await apiGet<{
      officials_total: number;
      appeals_total: number;
      flags_by_severity: Record<'high' | 'medium' | 'low', number>;
    }>(request, '/stats/overview');
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Обзор', level: 2 })).toBeVisible();
    await expect(page.getByText('Баллы риска рассчитаны:')).toBeVisible();
    const officialsCard = page.locator('.mantine-Card-root', { hasText: 'Служащие' }).first();
    await expect(officialsCard).toContainText(String(stats.officials_total));
    await expect(page.getByText(`высокий: ${stats.flags_by_severity.high}`)).toBeVisible();
    await expect(
      page.locator('.mantine-Card-root', { hasText: 'Обращения граждан' }).first(),
    ).toContainText(String(stats.appeals_total));
    const top = page.locator('.mantine-Card-root', { hasText: 'Топ-10 по риску' });
    await expect(tableRows(top)).toHaveCount(10);
    await expect(tableRows(top).filter({ hasText: SOKOLOV })).toBeVisible();
    await expectNoHorizontalScroll(page);
    await shot(page, '01-overview');
  });

  await test.step('0:45 Рейтинг: верх списка и top_flags', async () => {
    await page.getByRole('link', { name: 'Рейтинг служащих' }).click();
    await expect(page).toHaveURL(/\/officials$/);
    await expect(page.getByRole('heading', { name: 'Рейтинг служащих' })).toBeVisible();
    const rows = tableRows(page);
    await expect(rows).toHaveCount(20);
    const sokolovRow = rows.filter({ hasText: SOKOLOV });
    await expect(sokolovRow.locator('td').first()).toHaveText(String(before.rank));
    await expect(sokolovRow).toContainText('R01');
    await expect(page.getByText(/Найдено: \d+/)).toBeVisible();
    await expectNoHorizontalScroll(page);
    await shot(page, '02-rating-before');
  });

  await test.step('1:00 Обращения → «Новое»: демо-обращение через форму', async () => {
    await page.getByRole('link', { name: 'Обращения' }).click();
    await expect(page.getByRole('heading', { name: 'Обращения граждан' })).toBeVisible();
    await expect(tableRows(page).first()).toBeVisible();
    await expectNoHorizontalScroll(page);
    await shot(page, '03-appeals');

    await page.getByRole('link', { name: 'Новое обращение' }).click();
    await expect(page).toHaveURL(/\/appeals\/new$/);
    const textarea = page.getByLabel('Текст обращения');
    await textarea.fill(DEMO_TEXT);
    await expect(page.getByRole('button', { name: 'Отправить на анализ' })).toBeEnabled();
    await shot(page, '04-appeal-new');
    await page.getByRole('button', { name: 'Отправить на анализ' }).click();
    // Фоллбэк отвечает мгновенно, LLM на CPU — долго: фронт ждёт POST /appeals до 150 с
    await page.waitForURL(/\/appeals\/(?!new$)[^/]+$/, { timeout: 160_000 });
    appealId = new URL(page.url()).pathname.split('/').at(-1) ?? '';
    expect(appealId).not.toBe('');
  });

  await test.step('1:15 Разбор обращения: категория, сущности, сигналы, маршрут, привязка', async () => {
    const appeal = await apiGet<{
      status: string;
      linked_person_ids: string[];
      analysis: { category: string; engine?: string; entities: unknown[] } | null;
    }>(request, `/appeals/${appealId}`);
    const category = appeal.analysis?.category;
    // docs/demo.md: фоллбэк относит H1 к `procurement`, от LLM ждём `conflict_of_interest` (не проверено),
    // спикер называет категорию с экрана — поэтому принимаем обе
    expect(['conflict_of_interest', 'procurement']).toContain(category);
    note({ type: 'Разбор H1', description: `${appeal.analysis?.engine}: ${category}` });
    expect(appeal.linked_person_ids).toContain(before.id);

    await expect(page.getByRole('heading', { name: /Обращение от/ })).toBeVisible();
    await expect(
      page.getByText(category === 'procurement' ? 'Закупки' : 'Конфликт интересов', {
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.getByText(/Разбор: (LLM|правила)/)).toBeVisible();
    const marks = page.locator('mark');
    expect(await marks.count(), 'подсвечены сущности').toBeGreaterThanOrEqual(3);
    await expect(marks.filter({ hasText: 'Соколов Андрей Викторович' })).toBeVisible();
    await expect(marks.filter({ hasText: /ДорСтройРесурс/ })).toBeVisible();
    await expect(marks.filter({ hasText: /9,5 млн/ })).toBeVisible();
    await expect(page.getByText('Сигналы', { exact: true })).toBeVisible();
    await expect(page.getByText(/Конкретность сообщения: \d+/)).toBeVisible();
    await expect(page.getByText('Маршрут', { exact: true })).toBeVisible();
    const linked = page.locator('.mantine-Card-root', { hasText: 'Связанные служащие' });
    await expect(linked.getByRole('link', { name: SOKOLOV })).toBeVisible();
    await expectNoHorizontalScroll(page);
    await shot(page, '05-appeal');
    // Уведомление о регистрации закрываем, чтобы оно не перекрывало следующие экраны
    const toast = page.locator('.mantine-Notification-root', {
      hasText: 'Обращение зарегистрировано',
    });
    if (await toast.isVisible()) {
      await toast.locator('.mantine-Notification-closeButton').click();
      await expect(toast).toBeHidden();
    }
  });

  await test.step('1:45 Рейтинг: Соколов поднялся на 1-е место', async () => {
    const after = await standing(request, SOKOLOV);
    note({
      type: 'Соколов после обращения',
      description: `${after.rank}-е место, балл ${after.score}`,
    });
    expect(after.rank, 'после обращения Соколов первый').toBe(1);
    if (before.rank === 1) expect(after.score).toBeGreaterThanOrEqual(before.score);
    else expect(after.score, 'балл вырос').toBeGreaterThan(before.score);

    await page.getByRole('link', { name: 'Рейтинг служащих' }).click();
    const first = tableRows(page).first();
    await expect(first).toContainText(SOKOLOV);
    await expect(first.locator('td').first()).toHaveText('1');
    await expect(first).toContainText(String(after.score));
    await shot(page, '06-rating');
  });

  await test.step('2:00 Профиль Соколова: полномочия, флаги, объяснения, нормы', async () => {
    await tableRows(page).filter({ hasText: SOKOLOV }).click();
    await expect(page).toHaveURL(new RegExp(`/officials/${before.id}$`));
    await expect(page.getByRole('heading', { name: SOKOLOV, level: 2 })).toBeVisible();
    await expect(page.getByText(/ОКПД2: .*42\.11/)).toBeVisible();
    await expect(page.getByText(/Соколова Марина Олеговна/).first()).toBeVisible();
    for (const code of ['R01', 'R05', 'R06', 'R07', 'R08']) {
      await expect(
        page.locator('.mantine-Badge-label', { hasText: new RegExp(`^${code}$`) }),
      ).toBeVisible();
    }
    await expect(page.getByText(/ДорСтройРесурс/).first()).toBeVisible();
    await expect(page.getByText(/273-ФЗ ст\. 10/).first()).toBeVisible();
    await expect(page.getByText('Цепочка:').first()).toBeVisible();
    await expectNoHorizontalScroll(page);
    await shot(page, '07-profile');
    await shot(page, '07-profile-full', true);
  });

  const graph = page.getByTestId('relation-graph');

  await test.step('2:30 Граф: подсветка цепочки R01, номинальный директор, общий телефон', async () => {
    await expect(graph).toBeVisible();
    await expect(graph.locator('canvas').first()).toBeVisible();
    const flags = await apiGet<{
      items: { rule_code: string; evidence: { node_id: string; label: string }[] }[];
    }>(request, `/officials/${before.id}/flags`);
    const r01 = flags.items.find((f) => f.rule_code === 'R01');
    expect(r01, 'у Соколова есть R01').toBeTruthy();

    await page.getByText('Родственник — поставщик органа', { exact: true }).click();
    await expect(page.getByText('подсвечена цепочка R01')).toBeVisible();
    await expect
      .poll(async () => (await graphState(graph)).highlighted.length)
      .toBeGreaterThanOrEqual(4);
    const state = await graphState(graph);
    expect(state.highlighted).toContain(before.id);
    expect(state.faded, 'остальное приглушено').toBeGreaterThan(0);
    expect(state.highlightedEdges, 'подсвечены рёбра цепочки').toBeGreaterThanOrEqual(3);
    expect(state.highlightedLabels.join(' | ')).toMatch(/Соколова Марина Олеговна/);
    expect(state.highlightedLabels.join(' | ')).toMatch(/ДорСтройРесурс/);
    expect(state.highlightedLabels.join(' | ')).toMatch(/контракт/);
    await shot(page, '08-graph');

    // Клик по узлу компании: подпись в строке статуса
    const company = state.nodes.find(
      (n) => n.type === 'company' && state.highlighted.includes(n.id),
    );
    expect(company).toBeTruthy();
    await clickGraphNode(page, graph, company!.id);
    await expect(
      page.getByRole('status').filter({ hasText: /Компания: .*ДорСтройРесурс/ }),
    ).toBeVisible();

    // Общий телефон с братом супруги — R05
    await page.getByText('Общие контакты с подрядчиком', { exact: true }).click();
    await expect(page.getByText('подсвечена цепочка R05')).toBeVisible();
    await expect
      .poll(async () => (await graphState(graph)).highlightedLabels.join(' | '))
      .toMatch(/Кравцов/);
    await shot(page, '08-graph-r05');
  });

  await test.step('F-16: обращение видно в графе узлом, R07 в списке, переход по узлу', async () => {
    await page.getByText('Упоминания в обращениях', { exact: true }).click();
    await expect(page.getByText('подсвечена цепочка R07')).toBeVisible();
    await expect
      .poll(async () => (await graphState(graph)).nodes.some((n) => n.id === appealId))
      .toBe(true);
    await expect.poll(async () => (await graphState(graph)).highlighted).toContain(appealId);
    await shot(page, '09-graph-r07');
    await clickGraphNode(page, graph, appealId);
    await expect(page).toHaveURL(new RegExp(`/appeals/${appealId}$`));
    await page
      .locator('.mantine-Card-root', { hasText: 'Связанные служащие' })
      .getByRole('link', { name: SOKOLOV })
      .click();
    await expect(page).toHaveURL(new RegExp(`/officials/${before.id}$`));
    await expect(graph).toBeVisible();
  });

  await test.step('3:15 Профиль → «Сформировать докладную»', async () => {
    await page.getByRole('button', { name: 'Сформировать докладную' }).click();
    await page.waitForURL(/\/reports\/[^/]+$/, { timeout: 90_000 });
    await expect(page.getByRole('heading', { name: 'Докладная записка' })).toBeVisible();
    const doc = page.locator('.report-document');
    await expect(doc).toContainText('Соколов');
    await expect(doc).toContainText('273-ФЗ');
    await expect(doc).toContainText(/решени[ея]/i);
    await expect(page.getByRole('button', { name: 'Копировать текст' })).toBeVisible();
    await expect(
      page.getByRole('link', { name: new RegExp(`К профилю: ${SOKOLOV}`) }),
    ).toBeVisible();
    await expectNoHorizontalScroll(page);
    await shot(page, '10-report');
    await shot(page, '10-report-full', true);
  });

  await test.step('3:40 Рейтинг, фильтр по правилу: C2–C5', async () => {
    await page.getByRole('link', { name: 'Рейтинг служащих' }).click();
    const ruleSelect = page.getByRole('textbox', { name: 'Правило' });
    for (const { rule, name } of RULE_CASES) {
      await ruleSelect.click();
      await page.getByRole('option', { name: new RegExp(`^${rule} — `) }).click();
      await expect(page).toHaveURL(new RegExp(`rule_code=${rule}`));
      // Выборка на экране совпадает с ответом API на тот же фильтр (ждём смены данных:
      // пока идёт запрос, таблица показывает прошлую выборку)
      const api = await apiGet<{ items: ListItem[] }>(
        request,
        `/officials?rule_code=${rule}&sort=-risk_score&limit=20&offset=0`,
      );
      await expect
        .poll(() => tableRows(page).getByRole('link').allInnerTexts())
        .toEqual(api.items.map((i) => i.full_name));
      const top3 = api.items.slice(0, 3).map((i) => i.full_name);
      expect(top3, `${rule}: ${name} в первой тройке`).toContain(name);
      if (rule === 'R02') await shot(page, '11-rating-rule-r02');
    }
    await shot(page, '11-rating-rule');

    // N1 Орлов: одно расплывчатое обращение даёт только слабый сигнал — он внизу среди служащих с флагами
    const all = await apiGet<{ items: ListItem[] }>(
      request,
      '/officials?sort=-risk_score&limit=100&offset=0',
    );
    const flagged = all.items.filter((i) => i.top_flags.length > 0);
    const n1 = flagged.findIndex((i) => i.full_name === N1);
    expect(n1, `${N1} среди служащих с флагами`).toBeGreaterThanOrEqual(0);
    expect(flagged[n1].top_flags.map((f) => f.rule_code)).toEqual(['R07']);
    expect(n1 + 1, `${N1} в нижней четверти`).toBeGreaterThan(flagged.length * 0.75);
    note({ type: 'N1 Орлов', description: `${n1 + 1}-е из ${flagged.length} с флагами` });

    // Остальные фильтры рейтинга: поиск, мин. балл, сброс правила
    await page
      .locator('.mantine-InputWrapper-root', { hasText: 'Правило' })
      // Кнопка очистки Mantine помечена aria-hidden, поэтому ищем её по классу
      .locator('.mantine-InputClearButton-root')
      .click();
    await expect(page).not.toHaveURL(/rule_code=/);
    await page.getByRole('textbox', { name: 'Поиск' }).fill('Соколов');
    await expect(page).toHaveURL(/query=/);
    await expect(tableRows(page).filter({ hasText: SOKOLOV })).toBeVisible();
    await page.getByRole('textbox', { name: 'Поиск' }).fill('');
    await page.getByRole('textbox', { name: 'Мин. балл' }).fill('50');
    await expect(page).toHaveURL(/min_score=50/);
    await expect(tableRows(page).first()).toContainText(SOKOLOV);
  });

  await test.step('4:00 Ассистент: родственники среди подрядчиков', async () => {
    await page.getByRole('link', { name: 'Ассистент' }).click();
    await expect(page.getByRole('heading', { name: 'Ассистент аналитика' })).toBeVisible();
    await page.getByRole('button', { name: ASSISTANT_QUESTION }).click();
    const answer = page.getByText('Источники:');
    await expect(answer).toBeVisible({ timeout: 90_000 });
    await expect(page.getByRole('link', { name: SOKOLOV })).toBeVisible();
    await expectNoHorizontalScroll(page);
    await shot(page, '12-assistant');
    await page.getByRole('link', { name: SOKOLOV }).click();
    await expect(page).toHaveURL(new RegExp(`/officials/${before.id}$`));
  });

  expect(problems, 'ошибки консоли и HTTP 4xx/5xx').toEqual([]);
});

test('состояния экранов: пусто, ошибка API с повтором, не найдено', async ({ page }) => {
  // Пустая выборка рейтинга
  await page.goto('/officials?query=%D0%AF%D0%AF%D0%AF%D0%AF%D0%AF');
  await expect(page.getByText('По заданным фильтрам служащих не найдено')).toBeVisible();

  // Пустой список обращений
  await page.goto('/appeals?status=closed');
  await expect(page.getByText('Обращений нет')).toBeVisible();

  // 5xx от бэка: понятная ошибка и «Повторить», после восстановления — данные
  let failing = true;
  await page.route(`${API}/officials?*`, (route) =>
    failing
      ? route.fulfill({
          status: 503,
          contentType: 'application/problem+json',
          body: JSON.stringify({ title: 'ServiceUnavailable', detail: 'База данных недоступна' }),
        })
      : route.continue(),
  );
  await page.goto('/officials');
  await expect(page.getByText('Не удалось загрузить данные')).toBeVisible();
  await expect(page.getByText('База данных недоступна')).toBeVisible();
  await shot(page, '90-state-error');
  failing = false;
  await page.getByRole('button', { name: 'Повторить' }).click();
  await expect(tableRows(page)).toHaveCount(20);
  await page.unroute(`${API}/officials?*`);

  // 404 профиля: ошибка без повторных запросов
  const missing = `${API}/officials/00000000-0000-4000-8000-000000000000`;
  let profileRequests = 0;
  page.on('request', (req) => {
    if (req.url() === missing) profileRequests += 1;
  });
  await page.goto('/officials/00000000-0000-4000-8000-000000000000');
  await expect(page.getByText('Служащий не найден').first()).toBeVisible();
  await page.waitForTimeout(1500);
  expect(profileRequests, '4xx не повторяется').toBe(1);

  // Несуществующая докладная и неизвестный маршрут
  await page.goto('/reports/00000000-0000-4000-8000-000000000000');
  await expect(page.getByText('Черновик докладной не найден')).toBeVisible();
  await page.goto('/no-such-page');
  await expect(page.getByRole('heading', { name: 'Страница не найдена' })).toBeVisible();
});
