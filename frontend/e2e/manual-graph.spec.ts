import { expect, test } from './fixtures';
import { DEMO_ACCOUNT } from '../src/shared/config/demoAccount';

const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';

for (const theme of ['light', 'dark'])
  for (const width of [1440, 390]) {
    test(`ручная схема: создание, связь и reload, ${width}, ${theme}`, async ({
      page,
      request,
    }) => {
      await page.setViewportSize({ width, height: 950 });
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.addInitScript(
        (scheme) => localStorage.setItem('mantine-color-scheme-value', scheme),
        theme,
      );
      const { items } = await (await request.get(`${API}/officials?limit=1`)).json();
      await page.goto(`/officials/${items[0].id}`);
      await page.getByRole('button', { name: 'Дополнить граф', exact: true }).click();
      const editor = page.getByRole('dialog', { name: 'Дополнение графа' });
      await editor.getByRole('button', { name: 'Новая схема', exact: true }).click();
      await editor.getByLabel(/^Название схемы/).fill(`Проверка ${width} ${theme}`);
      await editor.getByRole('button', { name: 'Создать схему', exact: true }).click();
      await expect(editor.getByRole('tab', { name: 'Объекты', exact: true })).toBeVisible();
      const id = new URL(page.url()).searchParams.get('scheme');
      expect(id).toBeTruthy();
      try {
        await editor.getByLabel(/^Название объекта/).fill('Ручной объект');
        await editor.getByLabel('Пояснение к объекту', { exact: true }).fill('Требует проверки');
        await editor
          .getByLabel('Источник сведений об объекте', { exact: true })
          .fill('Рабочая заметка');
        await editor.getByRole('button', { name: 'Добавить объект', exact: true }).click();
        await expect(editor.getByText('Ручной объект', { exact: true })).toBeVisible();
        await editor.getByRole('tab', { name: 'Связи', exact: true }).click();
        await editor.getByLabel(/^От какого объекта/).click();
        await page
          .getByRole('option', { name: new RegExp(items[0].full_name.split(' ')[0]) })
          .first()
          .click();
        await editor.getByLabel(/^К какому объекту/).click();
        await page.getByRole('option', { name: 'Вручную: Ручной объект', exact: true }).click();
        await editor.getByLabel(/^Название связи/).fill('Совместный проект');
        await editor.getByRole('button', { name: 'Добавить связь', exact: true }).click();
        await expect(editor.getByText('Совместный проект', { exact: true })).toBeVisible();
        await page.screenshot({
          path: `../.codex-build/manual-graph-${width}-${theme}-editor.png`,
        });
        await page.keyboard.press('Escape');
        await expect(editor).not.toBeVisible();
        await expect(page.locator('[data-manual="true"]')).toBeVisible();
        await page.reload();
        await expect(page.locator('[data-manual="true"]')).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
          true,
        );
        await page.screenshot({
          path: `../.codex-build/manual-graph-${width}-${theme}.png`,
          fullPage: true,
        });
      } finally {
        await request.delete(`${API}/graph-workspaces/${id}`);
      }
    });
  }

test('схема доступна выбранному пользователю только для чтения, доступ отзывается', async ({
  page,
  request,
  browser,
}) => {
  const { items } = await (await request.get(`${API}/officials?limit=1`)).json();
  const root = items[0].id;
  const created = await request.post(`${API}/graph-workspaces`, {
    data: { title: 'Shared review', official_id: root },
  });
  expect(created.status()).toBe(201);
  const workspace = await created.json();
  const path = `${API}/graph-workspaces/${workspace.id}`;
  const node = await request.post(path + '/nodes', {
    data: { kind: 'company', label: 'Общая компания' },
  });
  expect(node.status()).toBe(201);
  const viewerContext = await browser.newContext();
  const viewer = await viewerContext.newPage();
  try {
    await page.goto(`/officials/${root}?scheme=${workspace.id}`);
    await page.getByRole('button', { name: 'Дополнить граф', exact: true }).click();
    const editor = page.getByRole('dialog', { name: 'Дополнение графа' });
    await editor.getByRole('tab', { name: 'Доступ', exact: true }).click();
    await editor.getByLabel('Кому дать доступ', { exact: true }).fill(DEMO_ACCOUNT.username);
    await page.getByRole('option', { name: DEMO_ACCOUNT.username, exact: true }).click();
    await editor.getByRole('button', { name: 'Сохранить доступ', exact: true }).click();
    await expect(editor.getByRole('status')).toContainText('Доступ сохранён');
    await viewer.goto('/login');
    await viewer.getByRole('button', { name: 'Аналитик', exact: true }).click();
    await viewer.getByRole('button', { name: 'Войти', exact: true }).click();
    await expect(viewer.getByRole('heading', { name: 'Обзор', exact: true })).toBeVisible();
    await viewer.goto(`/officials/${root}?scheme=${workspace.id}`);
    await expect(viewer.locator('[data-manual="true"]')).toBeVisible();
    await viewer.getByRole('button', { name: 'Дополнить граф', exact: true }).click();
    const reader = viewer.getByRole('dialog', { name: 'Дополнение графа' });
    await expect(reader.getByText('Только просмотр', { exact: true })).toBeVisible();
    await expect(reader.getByRole('button', { name: 'Добавить объект', exact: true })).toHaveCount(
      0,
    );
    await request.put(path + '/shares', { data: { user_ids: [] } });
    await viewer.reload();
    await expect(viewer.locator('[data-manual="true"]')).toHaveCount(0);
    await viewer.getByRole('button', { name: 'Дополнить граф', exact: true }).click();
    await expect(viewer.getByRole('alert')).toContainText('не найдена или доступ отозван');
  } finally {
    await viewerContext.close();
    await request.delete(path);
  }
});
