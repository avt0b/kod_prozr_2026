import { expect, test } from '@playwright/test';

const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';

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

test('презентация расширяет экран, сохраняет фильтр и закрывается по Escape', async ({ page }) => {
  await page.goto('/officials?min_score=40');
  await page.getByRole('button', { name: 'Режим презентации', exact: true }).click();
  await expect(page.locator('.workspace-shell')).toHaveAttribute('data-presentation', 'true');
  await expect(page.getByRole('navigation', { name: 'Разделы приложения' })).toBeHidden();
  await expect(page).toHaveURL(/min_score=40/);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('navigation', { name: 'Разделы приложения' })).toBeVisible();
  await expect(page).toHaveURL(/min_score=40/);
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
