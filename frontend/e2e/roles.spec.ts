import { expect, test } from '@playwright/test';
import { DEMO_ACCOUNTS } from '../src/shared/config/demoAccount';

const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';
const TEXT =
  'Сотрудник отдела закупок требует вознаграждение за включение фирмы в список поставщиков.';

test('гражданин регистрируется, подаёт обращение и не видит рабочее место', async ({ page }) => {
  const username = `citizen-${Date.now()}`;
  await page.goto('/login');
  await page.getByText('Регистрация', { exact: true }).click();
  await page.getByLabel(/^Логин/).fill(username);
  await page.getByLabel(/^Пароль/).fill('citizen-password-123');
  await page.getByLabel(/^Повторите пароль/).fill('citizen-password-123');
  await page.getByRole('button', { name: 'Зарегистрироваться', exact: true }).click();
  await expect(page).toHaveURL(/\/citizen$/);
  await expect(page.getByText('Вы ещё не подавали обращений.')).toBeVisible();

  await page.getByLabel(/^Текст обращения/).fill(TEXT);
  await page.getByRole('button', { name: 'Отправить', exact: true }).click();
  await expect(page.getByRole('status').getByText('Обращение отправлено')).toBeVisible({
    timeout: 150_000,
  });
  await expect(page.getByTestId('citizen-appeal')).toHaveCount(1);
  await expect(page.getByTestId('citizen-appeal')).toContainText('На рассмотрении');

  await page.goto('/officials');
  await expect(page).toHaveURL(/\/citizen$/);
  await page.goto('/admin/users');
  await expect(page).toHaveURL(/\/citizen$/);
});

test('администратор видит раздел пользователей, аналитик — нет', async ({ page, request }) => {
  const admin = DEMO_ACCOUNTS.admin;
  const login = await request.post(`${API}/auth/login`, { data: admin });
  test.skip(!login.ok(), 'Демо-учётка администратора не создана: make demo-user');

  await page.goto('/login');
  await page.getByRole('button', { name: 'Администратор', exact: true }).click();
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Обзор', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Пользователи' }).first().click();
  await expect(page.getByRole('heading', { name: 'Пользователи', exact: true })).toBeVisible();
  await expect(
    page.getByTestId('admin-user-row').filter({ hasText: admin.username }),
  ).toBeVisible();

  await page.getByRole('button', { name: 'Учётная запись', exact: true }).click();
  await page.getByRole('menuitem', { name: 'Выйти', exact: true }).click();
  await page.getByRole('button', { name: 'Аналитик', exact: true }).click();
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Обзор', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Пользователи' })).toHaveCount(0);
  await page.goto('/admin/users');
  await expect(page).toHaveURL(/\/$/);
});
