import { expect, test } from './fixtures';
import type { Core } from 'cytoscape';

const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';

for (const theme of ['light', 'dark'])
  for (const width of [1440, 390]) {
    test(`панель графа не сдвигается при выборе флага: ${width}, ${theme}`, async ({
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
      const picker = page.getByRole('group', { name: 'Сигнал на графе', exact: true });
      await expect(picker.getByText('R01', { exact: true })).toBeVisible();
      const before = await picker.boundingBox();
      await picker.getByText('R01', { exact: true }).click();
      const layout = page.getByRole('textbox', { name: 'Раскладка графа', exact: true });
      await expect(layout).toBeDisabled();
      await expect(layout).toHaveValue('По цепочке');
      const selected = await picker.boundingBox();
      expect(Math.abs(selected!.x - before!.x)).toBeLessThanOrEqual(1);
      expect(Math.abs(selected!.y - before!.y)).toBeLessThanOrEqual(1);
      await picker.getByText('Все связи', { exact: true }).click();
      await expect(layout).toBeEnabled();
      const restored = await picker.boundingBox();
      expect(Math.abs(restored!.x - before!.x)).toBeLessThanOrEqual(1);
      expect(Math.abs(restored!.y - before!.y)).toBeLessThanOrEqual(1);
    });
  }

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
    await expect(menu).toHaveAttribute('aria-expanded', 'false');

    const graph = page.getByTestId('relation-graph');
    await expect(graph.locator('canvas').first()).toBeVisible();
    const headerBottom = await page
      .locator('.profile-canvas-header')
      .evaluate((el) => el.getBoundingClientRect().bottom);
    const backTop = await page
      .getByRole('link', { name: 'К рейтингу служащих' })
      .evaluate((el) => el.getBoundingClientRect().top);
    expect(backTop).toBeGreaterThanOrEqual(headerBottom);
    if (width === 390) {
      const height = await page
        .locator('.profile-graph-viewport')
        .evaluate((el) => el.getBoundingClientRect().height);
      expect(height).toBeLessThanOrEqual(450);
    }
    if (width === 1440) {
      await graph.hover();
      await expect(page.locator('.profile-mesh')).toHaveAttribute('data-active', '');
    }
    const filters = page.getByRole('group', { name: 'Сигнал на графе' });
    await filters.getByText('R01', { exact: true }).click();
    await expect(page.getByText('подсвечена цепочка R01')).toBeVisible();
    const viewport = page.locator('.profile-graph-viewport');
    await expect(viewport.locator('.graph-edge-pill[data-highlighted]').first()).toBeVisible();
    const state = await viewport.evaluate(async (el) => {
      await Promise.allSettled(
        el
          .getAnimations({ subtree: true })
          .filter((animation) => animation.effect?.getComputedTiming().endTime !== Infinity)
          .map((animation) => animation.finished),
      );
      const core = el.querySelector('[data-testid="relation-graph"]') as HTMLElement & {
        _cyreg: { cy: Core };
      };
      const cy = core._cyreg.cy;
      const cards = Array.from(
        el.querySelectorAll('.graph-card[data-highlighted] .graph-card-face'),
      ).map((node) => node.getBoundingClientRect());
      const labels = Array.from(el.querySelectorAll('.graph-edge-pill[data-highlighted]')).map(
        (label) => ({
          text: label.textContent?.trim().replace(/\s+/g, ' '),
          box: label.getBoundingClientRect(),
        }),
      );
      const overlap = (a: DOMRect, b: DOMRect) =>
        a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
      return {
        count: labels.length,
        text: labels.map((label) => label.text),
        expected: cy
          .edges('.hl')
          .map((edge) => String(edge.data('label')).trim().replace(/\s+/g, ' ')),
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
    await expect(viewport.locator('.graph-link-track').first()).toHaveAttribute('d', / Q /);
    const halo = await viewport
      .locator('.graph-card[data-root]')
      .evaluate((node) => getComputedStyle(node, '::after').animationName);
    expect(halo).toBe('graph-halo');
    await expect(viewport.locator('.graph-link-flow').first()).toHaveCSS(
      'animation-name',
      'graph-travel',
    );

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
    if (width === 1440) {
      await page.getByRole('link', { name: bragina.full_name, exact: true }).click();
      await page.getByRole('link', { name: 'AI-анализ' }).click();
      await expect(page.getByRole('textbox', { name: 'Вопрос ассистенту' })).toHaveValue(
        `Какие риск-факторы и связи есть у служащего ${bragina.full_name}?`,
      );
    }
  });
}
