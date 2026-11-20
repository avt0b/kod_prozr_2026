import { expect, test } from '@playwright/test';
import { credentials } from './fixtures';

for (const width of [1440, 390]) {
  test(`вход, reload и выход, ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 950 });
    await page.goto('/officials?min_score=50');
    await expect(page).toHaveURL(/\/login$/);
    await page.getByLabel(/^Логин/).fill(credentials().username);
    await page.getByLabel(/^Пароль/).fill('incorrect-password');
    await page.getByRole('button', { name: 'Войти', exact: true }).click();
    await expect(page.getByRole('alert')).toContainText('Неверный логин или пароль');
    await page.getByLabel(/^Пароль/).fill(credentials().password);
    await page.getByRole('button', { name: 'Войти', exact: true }).click();
    await expect(page).toHaveURL(/\/officials\?min_score=50$/);
    await expect(page.locator('tbody tr').first()).toBeVisible();
    await page.reload();
    await expect(page.locator('tbody tr').first()).toBeVisible();
    expect(
      await page.evaluate(() =>
        Object.keys(localStorage).some((key) => /token|refresh|password/i.test(key)),
      ),
    ).toBe(false);
    expect(
      (await page.context().cookies()).find((cookie) => cookie.name === 'kodprozr_refresh')
        ?.httpOnly,
    ).toBe(true);
    await expect(page.getByRole('button', { name: 'Режим презентации', exact: true })).toHaveCount(
      0,
    );
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.getByRole('button', { name: 'Учётная запись', exact: true }).click();
    await page.getByRole('menuitem', { name: 'Выйти', exact: true }).click();
    await expect(page).toHaveURL(/\/login$/);
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Вход в кабинет' })).toBeVisible();
  });
}
