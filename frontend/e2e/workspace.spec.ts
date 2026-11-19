import { expect, test } from '@playwright/test';

const API = process.env.API_URL ?? 'http://localhost:8000/api/v1';

test('отложенный поиск сохраняет быстро изменённый минимальный балл', async ({ page }) => {
  await page.goto('/officials?query=%D0%A1%D0%BE%D0%BA%D0%BE%D0%BB%D0%BE%D0%B2');
  await page.getByRole('textbox', { name: 'Поиск', exact: true }).fill('');
  await page.getByRole('textbox', { name: 'Мин. балл', exact: true }).fill('50');
  await expect.poll(() => new URL(page.url()).searchParams.get('query')).toBeNull();
  await expect(page).toHaveURL(/min_score=50/);
  await expect(page.getByRole('textbox', { name: 'Мин. балл', exact: true })).toHaveValue('50');
});

test('анимации повторяются, счётчики завершаются, reduced motion показывает итог сразу', async ({
  page,
  request,
}) => {
  const stats = await (await request.get(`${API}/stats/overview`)).json();
  await page.goto('/');
  const counter = page
    .locator('.stat-panel')
    .first()
    .locator('.animated-number [aria-hidden="true"]');
  await counter.scrollIntoViewIfNeeded();
  await expect(counter).toHaveText(stats.officials_total.toLocaleString('ru-RU'));
  await page.getByRole('button', { name: 'Повторить анимации', exact: true }).click();
  await expect
    .poll(() => counter.textContent())
    .not.toBe(stats.officials_total.toLocaleString('ru-RU'));
  await expect(counter).toHaveText(stats.officials_total.toLocaleString('ru-RU'));
  await page.getByRole('button', { name: 'Повторить анимации', exact: true }).click();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(
    page.getByRole('button', { name: 'Повторить анимации', exact: true }),
  ).toBeDisabled();
  await expect(counter).toHaveText(stats.officials_total.toLocaleString('ru-RU'));
  expect(
    await page
      .locator('.network-edge')
      .first()
      .evaluate((element) => getComputedStyle(element).animationName),
  ).toBe('none');
});

test('повтор анимаций сохраняет вопрос и выбранный флаг', async ({ page, request }) => {
  await page.goto('/assistant');
  await page.getByRole('textbox', { name: 'Вопрос ассистенту' }).fill('Мой вопрос для проверки');
  await page.getByRole('button', { name: 'Повторить анимации', exact: true }).click();
  await expect(page.getByRole('textbox', { name: 'Вопрос ассистенту' })).toHaveValue(
    'Мой вопрос для проверки',
  );
  const top = await (
    await request.get(`${API}/officials?sort=-risk_score&limit=1&offset=0`)
  ).json();
  await page.goto(`/officials/${top.items[0].id}`);
  const flag = page.locator('.workspace-flag').first().getByRole('button');
  await flag.click();
  await expect(flag).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Повторить анимации', exact: true }).click();
  await expect(flag).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('[data-testid="relation-graph"]')).toBeVisible();
});

test('обзор связывает сводку, реальный граф и профиль первого в рейтинге', async ({
  page,
  request,
}) => {
  const stats = await (await request.get(`${API}/stats/overview`)).json();
  const top = await (
    await request.get(`${API}/officials?sort=-risk_score&limit=10&offset=0`)
  ).json();
  await page.goto('/');
  await expect(page.locator('.stat-panel').first()).toContainText(String(stats.officials_total));
  const focus = page.locator('.focus-case');
  await expect(focus).toContainText(top.items[0].full_name);
  await expect(focus.getByRole('img', { name: /Фрагмент графа связей/ })).toBeVisible();
  await expect(focus.getByRole('link', { name: 'Открыть профиль' })).toHaveAttribute(
    'href',
    `/officials/${top.items[0].id}`,
  );
  await focus.getByRole('link', { name: 'Открыть профиль' }).click();
  await expect(page.getByRole('heading', { name: top.items[0].full_name })).toBeVisible();
  await expect(page.locator('canvas').first()).toBeVisible();
});

test('поиск с клавиатуры открывает отфильтрованный рейтинг', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Control+k');
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'ФИО служащего' })).toBeFocused();
  await page.getByRole('textbox', { name: 'ФИО служащего' }).fill('Соколов');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page).toHaveURL(/officials\?query=/);
  await expect(page.locator('tbody')).toContainText('Соколов Андрей Викторович');
});

test('переход из прокрученного экрана возвращает начало страницы и доступные фильтры', async ({
  page,
}) => {
  await page.goto('/');
  await page.locator('.overview-ranking').scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => scrollY)).toBeGreaterThan(0);
  await page.getByRole('link', { name: 'Рейтинг служащих', exact: true }).click();
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
  for (const rule of ['R02', 'R03', 'R04', 'R05']) {
    await page.getByRole('textbox', { name: 'Правило', exact: true }).click();
    await page.getByRole('option', { name: new RegExp(`^${rule} — `) }).click();
    await expect(page).toHaveURL(new RegExp(`rule_code=${rule}`));
  }
});

test('подсказка ассистента отправляет вопрос и показывает проверяемые источники', async ({
  page,
}) => {
  await page.goto('/assistant');
  await expect(page.getByRole('button', { name: 'Отправить', exact: true })).toBeDisabled();
  const response = page.waitForResponse(
    (res) => res.url().endsWith('/assistant/ask') && res.request().method() === 'POST',
  );
  await page.getByRole('button', { name: /Найти скрытые связи/ }).click();
  const result = await (await response).json();
  const log = page.getByRole('log');
  await expect(log).toContainText(result.answer);
  await expect(log.getByText('Источники:')).toBeVisible();
  await expect(log.locator('a').first()).toBeVisible();
  await page.getByRole('textbox', { name: 'Вопрос ассистенту' }).fill('Проверка');
  await page.keyboard.press('Shift+Enter');
  await expect(page.getByRole('textbox', { name: 'Вопрос ассистенту' })).toHaveValue('Проверка\n');
});

for (const width of [390, 1440]) {
  for (const scheme of ['light', 'dark'] as const) {
    test(`экраны ${width}px, ${scheme}: навигация, контраст, отсутствие переполнения`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.emulateMedia({ reducedMotion: 'reduce', colorScheme: scheme });
      await page.addInitScript(
        (colorScheme) => localStorage.setItem('mantine-color-scheme-value', colorScheme),
        scheme,
      );
      const errors: string[] = [];
      page.on('pageerror', (error) => errors.push(error.message));
      for (const route of ['/', '/assistant', '/officials', '/risk-map', '/appeals']) {
        await page.goto(route);
        await expect(page.locator('.workspace-page-heading')).toBeVisible();
        await expect(page.locator('.workspace-state[role="status"]')).toHaveCount(0);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
          true,
        );
        const contrast = await page.evaluate(() => {
          const color = getComputedStyle(document.body);
          const luminance = (value: string) => {
            const channels = value
              .match(/\d+(\.\d+)?/g)!
              .slice(0, 3)
              .map(Number)
              .map((channel) => {
                const s = channel / 255;
                return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
              });
            return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
          };
          const foreground = luminance(color.color);
          const background = luminance(color.backgroundColor);
          return (
            (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05)
          );
        });
        expect(contrast).toBeGreaterThanOrEqual(4.5);
      }
      if (width === 390) {
        const assistant = page
          .getByRole('navigation', { name: 'Разделы приложения' })
          .getByRole('link', { name: 'Ассистент', exact: true });
        await assistant.click();
        await expect(page).toHaveURL(/assistant$/);
        await expect(assistant).toHaveAttribute('aria-current', 'page');
        const lastSuggestion = page.getByRole('button', { name: /Определить приоритет/ });
        await lastSuggestion.scrollIntoViewIfNeeded();
        await expect(lastSuggestion).toBeInViewport();
        expect(
          await lastSuggestion.evaluate((element) => {
            const r = element.getBoundingClientRect();
            return element.contains(
              document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2),
            );
          }),
        ).toBe(true);
      }
      expect(errors).toEqual([]);
    });
  }
}
