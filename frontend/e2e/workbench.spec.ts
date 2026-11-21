import { expect, test } from './fixtures';

test('запрос старой сессии не повторяется под другой учётной записью', async ({ page }) => {
  await page.goto('/officials');
  await expect(page.locator('tbody tr').first()).toBeVisible();
  let writes = 0;
  await page.route('**/api/v1/appeals', async (route) => {
    writes += 1;
    await route.fulfill({ status: 401, json: { detail: 'Expired' } });
  });
  await page.route('**/api/v1/auth/refresh', (route) =>
    route.fulfill({
      json: {
        access_token: 'not-a-real-token',
        session_id: 'different-session',
        user: { id: 'another-user', username: 'other' },
      },
    }),
  );
  const result = await page.evaluate(async (modulePath) => {
    const { request } = await import(modulePath);
    try {
      await request('POST', '/appeals', { body: { text: 'Must never be replayed' } });
      return 'unexpected success';
    } catch (error) {
      return error instanceof Error ? error.message : String(error);
    }
  }, '/src/shared/api/client.ts');
  expect(result).toContain('Сессия изменилась');
  expect(writes).toBe(1);
});

const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';

test('смена сессии загружает новые данные вместо кеша предыдущего аккаунта', async ({
  page,
  request,
}) => {
  const data = await (await request.get(`${API}/officials?limit=20`)).json();
  let switched = false;
  await page.route('**/api/v1/officials?*', (route) =>
    route.fulfill({
      json: switched ? { items: [{ ...data.items[0], full_name: 'Сессия Б' }], total: 1 } : data,
    }),
  );
  await page.goto('/officials');
  await expect(page.locator('tbody tr').first()).toBeVisible();
  await page.route('**/api/v1/__switch', (route) => route.fulfill({ status: 401, json: {} }));
  await page.route('**/api/v1/auth/refresh', (route) => {
    switched = true;
    return route.fulfill({
      json: {
        access_token: 'mock-new-token',
        session_id: 'new-session',
        user: { id: 'new-user', username: 'new' },
      },
    });
  });
  await page.evaluate(async (path) => {
    const { request } = await import(path);
    await request('POST', '/__switch', {}).catch(() => undefined);
  }, '/src/shared/api/client.ts');
  await expect(page.getByRole('link', { name: 'Сессия Б', exact: true })).toBeVisible();
});

test('запоздалый ответ старой сессии не возвращается после смены аккаунта', async ({ page }) => {
  await page.goto('/officials');
  await expect(page.locator('tbody tr').first()).toBeVisible();
  const message = await page.evaluate(
    async (paths) => {
      const client = await import(paths.client);
      const original = window.fetch;
      let release!: () => void;
      let started!: () => void;
      const bodyGate = new Promise<void>((resolve) => {
        release = resolve;
      });
      const bodyStarted = new Promise<void>((resolve) => {
        started = resolve;
      });
      window.fetch = async (...args) => {
        const path = String(args[0]);
        if (path.endsWith('/reports/__delayed')) {
          const response = new Response('{}');
          response.text = async () => {
            started();
            await bodyGate;
            return '{"id":"old-user-report"}';
          };
          return response;
        }
        if (path.endsWith('/switch-session')) return new Response('{}', { status: 401 });
        if (path.endsWith('/auth/refresh'))
          return new Response(
            JSON.stringify({
              access_token: 'mock-token',
              session_id: 'different-session',
              user: { id: 'different-user', username: 'other' },
            }),
          );
        return original(...args);
      };
      try {
        const pending = client.request('POST', '/reports/__delayed', {}).then(
          () => 'unexpected success',
          (error: Error) => error.message,
        );
        await bodyStarted;
        await client.request('GET', '/switch-session', {}).catch(() => undefined);
        release();
        return await pending;
      } finally {
        window.fetch = original;
      }
    },
    { client: '/src/shared/api/client.ts', session: '/src/shared/lib/authSession.ts' },
  );
  expect(message).toContain('Сессия изменилась');
});

test('на телефоне второй кейс добавляется в панели и все отметки видны без боковой прокрутки', async ({
  page,
  request,
}) => {
  const { items } = await (
    await request.get(`${API}/officials?sort=-risk_score&limit=2&offset=0`)
  ).json();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/officials');
  await page.getByRole('button', { name: 'Инструменты аналитика', exact: true }).click();
  await page.getByRole('menuitem', { name: /Сравнение/ }).click();
  const panel = page.getByRole('dialog', { name: 'Сравнение служащих' });
  await panel.getByRole('button', { name: 'Добавить служащего', exact: true }).click();
  for (const item of items) {
    await panel
      .getByRole('textbox', { name: 'Поиск служащего для сравнения', exact: true })
      .fill(item.full_name);
    await panel
      .getByRole('button', { name: `Добавить в сравнение: ${item.full_name}`, exact: true })
      .click();
  }
  await expect(panel.locator('.comparison-case')).toHaveCount(2);
  await expect(panel.locator('.rule-mobile-matrix')).toBeVisible();
  await expect(panel.locator('.rule-mobile-cases').first().getByRole('group')).toHaveCount(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('из панели можно добавить первого, второго и третьего служащего, затем заменить выбранного', async ({
  page,
  request,
}) => {
  const { items } = await (
    await request.get(`${API}/officials?sort=-risk_score&limit=3&offset=0`)
  ).json();
  await page.goto('/officials');
  await page.getByRole('button', { name: 'Открыть сравнение', exact: true }).click();
  const panel = page.getByRole('dialog', { name: 'Сравнение служащих' });
  const add = panel.getByRole('button', { name: 'Добавить служащего', exact: true });
  await add.click();
  const search = panel.getByRole('textbox', { name: 'Поиск служащего для сравнения', exact: true });
  await expect(search).toBeFocused();
  await search.fill(items[0].full_name);
  await panel
    .getByRole('button', { name: `Добавить в сравнение: ${items[0].full_name}`, exact: true })
    .click();
  await expect(panel.locator('.comparison-case')).toHaveCount(1);
  await expect(search).toHaveValue('');
  await expect(add).toBeEnabled();
  await panel.getByRole('button', { name: 'Закрыть выбор служащего', exact: true }).click();
  await panel.getByRole('button', { name: 'Добавить служащего', exact: true }).click();
  await search.fill(items[1].full_name);
  await panel
    .getByRole('button', { name: `Добавить в сравнение: ${items[1].full_name}`, exact: true })
    .click();
  await expect(panel.locator('.comparison-case')).toHaveCount(2);
  await expect(panel.getByRole('table', { name: 'Совпадения правил по служащим' })).toBeVisible();
  await expect(panel.locator('.rule-matrix tr[data-shared]').first()).toBeVisible();
  await search.fill(items[2].full_name);
  await panel
    .getByRole('button', { name: `Добавить в сравнение: ${items[2].full_name}`, exact: true })
    .click();
  await expect(panel.locator('.comparison-case')).toHaveCount(3);
  await expect(add).toBeDisabled();
  await expect(
    panel.getByText('Все три места заняты. Уберите кейс, чтобы добавить другого служащего.'),
  ).toBeVisible();
  await panel
    .getByRole('button', { name: `Убрать из сравнения: ${items[1].full_name}`, exact: true })
    .click();
  await expect(add).toBeEnabled();
  await search.fill(items[1].full_name);
  await panel
    .getByRole('button', { name: `Добавить в сравнение: ${items[1].full_name}`, exact: true })
    .click();
  await expect(panel.locator('.comparison-case')).toHaveCount(3);
  await expect(page).toHaveURL(/\/officials$/);
});

test('сохранённый кейс остаётся после перезагрузки, открывается и удаляется', async ({
  page,
  request,
}) => {
  const { items } = await (
    await request.get(`${API}/officials?sort=-risk_score&limit=1&offset=0`)
  ).json();
  const person = items[0];
  await page.goto('/officials');
  await page
    .getByRole('button', { name: `Сохранить кейс: ${person.full_name}`, exact: true })
    .click();
  await expect(page).toHaveURL(/\/officials$/);
  await page.reload();
  await page.getByRole('button', { name: 'Открыть сохранённые кейсы', exact: true }).click();
  const panel = page.getByRole('dialog', { name: 'Сохранённые кейсы' });
  await expect(panel).toContainText('На этом устройстве');
  await panel.getByRole('link', { name: person.full_name, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/officials/${person.id}$`));
  await expect(panel).toBeHidden();
  await page
    .getByRole('main')
    .getByRole('button', { name: `Убрать из сохранённых: ${person.full_name}`, exact: true })
    .click();
  await page.getByRole('button', { name: 'Открыть сохранённые кейсы', exact: true }).click();
  await expect(panel.getByRole('heading', { name: 'Важные кейсы — под рукой' })).toBeVisible();
});

test('сравнение ограничено тремя кейсами и показывает показатели API', async ({
  page,
  request,
}) => {
  const { items } = await (
    await request.get(`${API}/officials?sort=-risk_score&limit=4&offset=0`)
  ).json();
  await page.goto('/officials');
  for (const item of items)
    await page
      .getByRole('button', { name: `Добавить к сравнению: ${item.full_name}`, exact: true })
      .click();
  await expect(
    page.getByText('В сравнении уже три кейса. Уберите один, чтобы добавить новый.'),
  ).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Открыть сравнение', exact: true }).click();
  const panel = page.getByRole('dialog', { name: 'Сравнение служащих' });
  await expect(panel.locator('.comparison-case')).toHaveCount(3);
  await expect(panel).toContainText('3 из 3 кейсов');
  await expect(
    panel.locator('.comparison-case').first().locator('.workspace-risk-badge'),
  ).toHaveText(String(items[0].risk_score));
  await panel
    .getByRole('button', { name: `Убрать из сравнения: ${items[1].full_name}`, exact: true })
    .click();
  await expect(panel.locator('.comparison-case')).toHaveCount(2);
  await panel.getByRole('button', { name: 'Очистить сравнение', exact: true }).click();
  await expect(panel.getByRole('heading', { name: 'Служащие не выбраны' })).toBeVisible();
});

test('ошибка загрузки сравниваемого профиля не превращается в вымышленные показатели', async ({
  page,
  request,
}) => {
  const { items } = await (
    await request.get(`${API}/officials?sort=-risk_score&limit=1&offset=0`)
  ).json();
  await page.goto('/officials');
  await page
    .getByRole('button', { name: `Добавить к сравнению: ${items[0].full_name}`, exact: true })
    .click();
  await page.route(`**/api/v1/officials/${items[0].id}`, (route) =>
    route.fulfill({
      status: 404,
      contentType: 'application/problem+json',
      body: JSON.stringify({ title: 'NotFound', detail: 'Кейс недоступен' }),
    }),
  );
  await page.getByRole('button', { name: 'Открыть сравнение', exact: true }).click();
  const panel = page.getByRole('dialog', { name: 'Сравнение служащих' });
  await expect(panel.getByText('Не удалось загрузить данные')).toBeVisible();
  await expect(panel.locator('.comparison-metrics')).toHaveCount(0);
  await panel
    .getByRole('button', { name: `Убрать из сравнения: ${items[0].full_name}`, exact: true })
    .click();
  await expect(panel.getByRole('heading', { name: 'Служащие не выбраны' })).toBeVisible();
});

test('мобильные инструменты доступны из меню и панели не переполняют экран', async ({
  page,
  request,
}) => {
  const { items } = await (
    await request.get(`${API}/officials?sort=-risk_score&limit=1&offset=0`)
  ).json();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/officials/${items[0].id}`);
  await page
    .getByRole('button', { name: `Сохранить кейс: ${items[0].full_name}`, exact: true })
    .click();
  await page.getByRole('button', { name: 'Инструменты аналитика', exact: true }).click();
  await page.getByRole('menuitem', { name: /Сохранённые кейсы/ }).click();
  const panel = page.getByRole('dialog', { name: 'Сохранённые кейсы' });
  await expect(panel.getByRole('link', { name: items[0].full_name, exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.keyboard.press('Escape');
  await expect(panel).toBeHidden();
});
