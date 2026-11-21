import { expect, test } from './fixtures';

const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';

for (const theme of ['light', 'dark']) {
  for (const width of [1440, 390]) {
    test(`дизайн-ревью: ${theme}, ${width}px`, async ({ page, request }) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.addInitScript(
        (scheme) => localStorage.setItem('mantine-color-scheme-value', scheme),
        theme,
      );
      const { items } = await (
        await request.get(`${API}/officials?sort=-risk_score&limit=3&offset=0`)
      ).json();
      await page.goto('/officials?min_score=40');
      await expect(page.locator('html')).toHaveAttribute('data-mantine-color-scheme', theme);
      const active = page.getByRole('textbox', { name: 'Мин. балл', exact: true });
      const inactive = page.getByRole('textbox', { name: 'Поиск', exact: true });
      expect(await active.evaluate((el) => getComputedStyle(el).backgroundColor)).not.toBe(
        await inactive.evaluate((el) => getComputedStyle(el).backgroundColor),
      );
      await expect(page.locator('th[aria-sort="descending"]')).toContainText('Балл');
      expect(
        await page
          .locator('tbody td')
          .first()
          .evaluate((el) => getComputedStyle(el).textAlign),
      ).toBe('right');
      await page.screenshot({
        path: `../.codex-build/review-2026-11-19/after-rating-${theme}-${width}.png`,
        fullPage: true,
      });
      for (const item of items)
        await page
          .getByRole('button', { name: `Добавить к сравнению: ${item.full_name}`, exact: true })
          .click();
      await expect(page.locator('tr[data-compared]')).toHaveCount(3);
      if (width === 390) {
        await page.getByRole('button', { name: 'Инструменты аналитика', exact: true }).click();
        await page.getByRole('menuitem', { name: /Сравнение/ }).click();
      } else await page.getByRole('button', { name: 'Открыть сравнение', exact: true }).click();
      const panel = page.getByRole('dialog', { name: 'Сравнение служащих' });
      await expect(panel.locator('.comparison-case')).toHaveCount(3);
      await expect(
        panel.getByText('Все три места заняты. Уберите кейс, чтобы добавить другого служащего.'),
      ).toBeVisible();
      await expect(panel.locator('.comparison-add')).toHaveCount(0);
      await expect(panel.locator('.rule-comparison')).toBeVisible();
      expect(await panel.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
      await page.screenshot({
        path: `../.codex-build/review-2026-11-19/after-comparison-${theme}-${width}.png`,
        fullPage: true,
      });
      await page.keyboard.press('Escape');
      await expect(panel).toBeHidden();
      await page.goto(`/officials/${items[0].id}`);
      const flag = page
        .locator('.workspace-flag')
        .filter({ hasText: 'Родственник — поставщик органа' })
        .first();
      await flag.getByRole('button', { name: /Родственник — поставщик органа/ }).click();
      await expect(flag.getByText('Факт и пояснение', { exact: true })).toBeVisible();
      await expect(flag.getByText('Записи-источники', { exact: true })).toBeVisible();
      await expect(flag.getByText('Правовое основание', { exact: true })).toBeVisible();
      const readMore = flag.getByRole('button', { name: 'Читать полностью' });
      await expect(readMore).toHaveAttribute('aria-expanded', 'false');
      await readMore.click();
      await expect(flag.getByRole('button', { name: 'Свернуть пояснение' })).toHaveAttribute(
        'aria-expanded',
        'true',
      );
      await flag.getByRole('button', { name: 'Свернуть пояснение' }).click();
      const sources = flag.getByText('Записи-источники', { exact: true });
      await expect(flag.locator('ol')).toBeHidden();
      await sources.click();
      await expect(flag.locator('li').first()).toBeVisible();
      await sources.click();
      const graph = page.getByTestId('relation-graph');
      await expect(graph.locator('canvas').first()).toBeVisible();
      await graph.scrollIntoViewIfNeeded();
      await page.screenshot({
        path: `../.codex-build/review-2026-11-19/after-graph-${theme}-${width}.png`,
        fullPage: true,
      });
    });
  }
}

test('при загрузке сравнения отсутствующие данные не объявляются отсутствием сигнала', async ({
  page,
  request,
}) => {
  const { items } = await (
    await request.get(`${API}/officials?sort=-risk_score&limit=2&offset=0`)
  ).json();
  await page.goto('/officials');
  for (const item of items)
    await page
      .getByRole('button', { name: `Добавить к сравнению: ${item.full_name}`, exact: true })
      .click();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(`**/api/v1/officials/${items[1].id}`, async (route) => {
    await gate;
    await route.continue();
  });
  await page.getByRole('button', { name: 'Открыть сравнение', exact: true }).click();
  const panel = page.getByRole('dialog', { name: 'Сравнение служащих' });
  await expect(panel.getByRole('status', { name: 'Загрузка данных' }).first()).toBeVisible();
  await expect(panel.getByText('Не выявлен', { exact: true })).toHaveCount(0);
  await expect(panel.locator('.rule-comparison')).toHaveCount(0);
  release();
  await expect(panel.locator('.rule-comparison')).toBeVisible();
});
