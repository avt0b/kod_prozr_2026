import { expect, test } from '@playwright/test';
import type { Core } from 'cytoscape';

const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';

for (const width of [1440, 390]) {
  test(`холст профиля и читаемые подписи связей, ${width}px`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 900 });
    const { items } = await (await request.get(`${API}/officials?query=Брагина&limit=10`)).json();
    const bragina = items.find(
      (item: { full_name: string }) => item.full_name === 'Брагина Ольга Олеговна',
    );
    expect(bragina).toBeTruthy();

    const rating = '/officials?min_score=70';
    await page.goto(rating);
    await page.getByRole('link', { name: bragina.full_name, exact: true }).click();
    await expect(page.getByRole('heading', { name: bragina.full_name, exact: true })).toBeVisible();

    const menu = page.getByRole('button', { name: 'Код прозрачности', exact: true });
    await expect(menu).toHaveAttribute('aria-expanded', 'false');
    await menu.click();
    await expect(
      page
        .getByRole('navigation', { name: 'Разделы приложения' })
        .getByRole('link', { name: 'Карта рисков' }),
    ).toBeVisible();
    await menu.click();

    const graph = page.getByTestId('relation-graph');
    await expect(graph.locator('canvas').first()).toBeVisible();
    const filters = page.getByRole('group', { name: 'Сигнал на графе' });
    await filters.getByText('R01', { exact: true }).click();
    await expect(page.getByText('подсвечена цепочка R01')).toBeVisible();
    const state = await graph.evaluate((el) => {
      const cy = (el as HTMLElement & { _cyreg: { cy: Core } })._cyreg.cy;
      const cards = cy.nodes('.hl').map((node) =>
        node.renderedBoundingBox({
          includeLabels: false,
          includeOverlays: false,
        }),
      );
      const labels = cy.edges('.hl').map((edge) => ({
        text: edge.style('label'),
        source: edge.data('label') as string,
        box: edge.renderedBoundingBox({
          includeEdges: false,
          includeOverlays: false,
          includeLabels: true,
        }),
      }));
      const overlap = (a: (typeof cards)[number], b: (typeof cards)[number]) =>
        a.x1 < b.x2 && b.x1 < a.x2 && a.y1 < b.y2 && b.y1 < a.y2;

      return {
        count: labels.length,
        text: labels.map((label) => label.text),
        expected: labels.map((label) => label.source),
        overlaps: labels
          .filter(
            ({ box }, index) =>
              cards.some((card) => overlap(card, box)) ||
              labels.slice(0, index).some((other) => overlap(other.box, box)),
          )
          .map((label) => label.text),
      };
    });
    expect(state.count).toBeGreaterThanOrEqual(4);
    expect(state.text).toEqual(state.expected);
    expect(state.overlaps).toEqual([]);

    const inspector = page.getByRole('complementary', { name: 'Инспектор графа' });
    const picker = inspector.getByRole('textbox', { name: 'Сущность на графе' });
    await picker.fill('СибЛиния');
    await page.getByRole('option', { name: /СибЛиния/ }).click();
    await expect(inspector.getByRole('heading', { name: /СибЛиния/ })).toBeVisible();
    await expect(inspector.getByRole('heading', { name: 'Связанные сущности' })).toBeVisible();
    await inspector.getByRole('button', { name: 'Свернуть инспектор' }).click();
    await expect(page.getByRole('button', { name: 'Инспектор', exact: true })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.getByRole('link', { name: 'К рейтингу служащих' }).click();
    await expect(page).toHaveURL(new RegExp(`${rating.replace('?', '\\?')}$`));
  });
}
