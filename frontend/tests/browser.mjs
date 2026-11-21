/** Run against an already started frontend. TEST_API_URL enables real-API assertions. */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const base = process.env.TEST_BASE_URL ?? 'http://127.0.0.1:5173';
const api = process.env.TEST_API_URL;
const browser = await chromium.launch({
  headless: true,
  ...(process.env.TEST_BROWSER_CHANNEL ? { channel: process.env.TEST_BROWSER_CHANNEL } : {}),
});
const errors = [];
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.setDefaultTimeout(15_000);
page.on('pageerror', (error) => errors.push(error.message));
await fs.mkdir('test-results', { recursive: true });
try {
  const credentials =
    process.env.E2E_USERNAME && process.env.E2E_PASSWORD
      ? { username: process.env.E2E_USERNAME, password: process.env.E2E_PASSWORD }
      : JSON.parse(
          await fs.readFile(new URL('../../.codex-build/local-auth.json', import.meta.url), 'utf8'),
        );
  const login = await context.request.post(`${base}/api/v1/auth/login`, {
    data: credentials,
  });
  assert.equal(login.status(), 200, 'Provision an E2E user before running browser tests');
  const { access_token } = await login.json();
  if (api) {
    const result = await (
      await fetch(`${api}/appeals?limit=20&offset=0`, {
        headers: { Authorization: `Bearer ${access_token}` },
      })
    ).json();
    await page.route('**/api/v1/appeals?*', async (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: result.items, total: 45 }),
      }),
    );
    await page.goto(`${base}/appeals`);
    const next = page.waitForRequest(
      (request) =>
        request.url().includes('/api/v1/appeals?') &&
        new URL(request.url()).searchParams.get('offset') === '20',
    );
    await page.getByRole('button', { name: '2', exact: true }).click();
    await next;
    assert.equal(new URL(page.url()).searchParams.get('page'), '2');
    await page.unroute('**/api/v1/appeals?*');
  }
  // Invalid URL values must never produce negative/NaN API offsets.
  await page.goto(`${base}/appeals?page=-2&status=invalid&category=invalid`);
  await page.getByRole('heading', { name: 'Обращения граждан' }).waitFor();
  await page.getByRole('columnheader', { name: 'Уверенность' }).waitFor();
  await page.getByRole('columnheader', { name: 'Связанные служащие' }).waitFor();
  await page.getByRole('textbox', { name: 'Статус', exact: true }).click();
  await page.getByRole('option', { name: 'Новое', exact: true }).click();
  assert.equal(new URL(page.url()).searchParams.get('status'), 'new');
  assert.equal(new URL(page.url()).searchParams.get('page'), null);
  // Form and inline failure handling; creating mutations must not be retried automatically.
  await page.getByRole('link', { name: 'Новое обращение' }).click();
  await page.getByLabel('Текст обращения').fill('Коротко');
  assert.equal(await page.getByRole('button', { name: 'Отправить на анализ' }).isDisabled(), true);
  await page.getByRole('button', { name: 'Вставить пример' }).click();
  const text = await page.getByLabel('Текст обращения').inputValue();
  assert.match(text, /^Здравствуйте\. Хочу сообщить/);
  if (api) {
    await page.route('**/api/v1/appeals', async (route) => {
      if (route.request().method() === 'POST') {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Тестовая ошибка сервиса' }),
        });
      } else await route.continue();
    });
    await page.getByRole('button', { name: 'Отправить на анализ' }).click();
    await page.getByRole('status').filter({ hasText: 'Обращение анализируется' }).waitFor();
    await page.getByText('Тестовая ошибка сервиса').waitFor();
    assert.equal(await page.getByLabel('Текст обращения').inputValue(), text);
    await page.unroute('**/api/v1/appeals');
  }
  await page.getByRole('button', { name: 'Отправить на анализ' }).click();
  await page.waitForURL(/\/appeals\/(?!new)[^/]+$/);
  const appealId = new URL(page.url()).pathname.split('/').at(-1);
  await page.getByRole('link', { name: 'Соколов Андрей Викторович' }).waitFor();
  if (!api) await page.getByText('Конфликт интересов', { exact: true }).waitFor();
  await page.screenshot({ path: 'test-results/appeal.png', fullPage: true });
  await page.getByRole('button', { name: 'Повторить анализ' }).click();
  await page.getByRole('link', { name: 'Соколов Андрей Викторович' }).click();
  await page.getByTestId('relation-graph').waitFor();
  const profileId = new URL(page.url()).pathname.split('/').at(-1);
  await page.getByText('Родственник — поставщик органа', { exact: true }).click();
  await page.getByText('подсвечена цепочка R01').waitFor();
  await page.getByRole('button', { name: 'Вписать граф' }).click();
  const container = page.getByTestId('relation-graph');
  // Inspect our own Cytoscape instance, then click actual canvas coordinates.
  const nodeInfo = await container.evaluate((el) => {
    const cy = el._cyreg.cy;
    return {
      highlighted: cy.nodes('.hl').map((n) => n.id()),
      contracts: cy.nodes('[type="contract"]').map((n) => n.data('label')),
    };
  });
  assert.ok(nodeInfo.highlighted.length >= 5);
  assert.ok(nodeInfo.contracts.some((label) => label.includes('5 контрактов')));
  // The mock fixture has another amount; real demo values come from the API.
  if (!api) assert.ok(nodeInfo.contracts.some((label) => label.includes('86,')));
  await page.screenshot({ path: 'test-results/profile.png', fullPage: true });
  if (api) {
    const personId = new URL(page.url()).pathname.split('/').at(-1);
    const graph = await (
      await fetch(`${api}/officials/${personId}/graph`, {
        headers: { Authorization: `Bearer ${access_token}` },
      })
    ).json();
    assert.ok(graph.nodes.some((n) => n.id === appealId && n.type === 'appeal'));
    const flags = await (
      await fetch(`${api}/officials/${personId}/flags`, {
        headers: { Authorization: `Bearer ${access_token}` },
      })
    ).json();
    assert.ok(flags.items.some((f) => f.rule_code === 'R07'));
  }
  await page.getByText('Родственник — поставщик органа', { exact: true }).click();
  const position = await container.evaluate((el) => {
    const node = el._cyreg.cy.nodes('[type="appeal"]').first();
    return { id: node.id(), ...node.renderedPosition() };
  });
  const bounds = await container.boundingBox();
  await page.mouse.click(bounds.x + position.x, bounds.y + position.y);
  await page.getByRole('link', { name: 'Открыть обращение' }).click();
  await page.waitForURL(new RegExp(`/appeals/${position.id}$`));
  await page.getByRole('link', { name: 'Соколов Андрей Викторович' }).click();
  await page.getByRole('button', { name: 'Сформировать докладную' }).click();
  await page.waitForURL(/\/reports\//);
  await page.getByText('Черновик', { exact: false }).first().waitFor();
  // Dense graph and theme switch stress only our real HTTP boundary.
  if (api) {
    const personId = profileId;
    await page.route('**/api/v1/officials/*/graph?*', async (route) => {
      const nodes = [
        { id: personId, type: 'person', label: 'Корневой узел' },
        ...Array.from({ length: 149 }, (_, i) => ({
          id: `stress-${i}`,
          type: ['person', 'company', 'organ', 'contract', 'appeal'][i % 5],
          label: `Тестовый узел ${i}`,
        })),
      ];
      const edges = nodes.slice(1).map((node, i) => ({
        source: i < 10 ? personId : nodes[1 + (i % 10)].id,
        target: node.id,
        type: 'kinship',
        label: 'связь',
      }));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ nodes, edges, truncated: true }),
      });
    });
    await page.goto(`${base}/officials/${personId}`);
    await page.getByTestId('relation-graph').waitFor();
    await page.getByText('Показана часть связей', { exact: false }).waitFor();
    assert.equal(
      await page.getByTestId('relation-graph').evaluate((el) => el._cyreg.cy.nodes().length),
      150,
    );
    await page.getByRole('textbox', { name: 'Раскладка графа' }).click();
    await page.getByRole('option', { name: 'Силовая' }).click();
    assert.equal(
      await page.getByTestId('relation-graph').evaluate((el) => el._cyreg.cy.nodes().length),
      150,
    );
    await page.getByRole('button', { name: 'Сменить тему' }).click();
    await page.locator('canvas').first().waitFor();
    assert.equal(
      await page.getByTestId('relation-graph').evaluate((el) => el._cyreg.cy.nodes().length),
      150,
    );
    await page.screenshot({ path: 'test-results/graph-150.png', fullPage: true });
  }
  assert.deepEqual(errors, []);
  console.log(
    `PASS ${api ? 'real API' : 'mocks'}: filters, validation, create, reanalyze, profile, R01, canvas navigation, report${api ? ', API R07, 150-node graph' : ''}`,
  );
} finally {
  await browser.close();
}
