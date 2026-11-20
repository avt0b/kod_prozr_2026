import { expect, test } from './fixtures';

const endpoint = '**/api/v1/assistant/ask';
const answer = 'Откройте цифровой профиль и сверьте цепочку поставщиков с первоисточниками.';
const source = { type: 'person', id: 'example', label: 'Профиль для проверки' };

for (const width of [1440, 390]) {
  test(`Алексей следит за вводом и остаётся слева от ответа, ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 930 });
    let finish!: () => void;
    const release = new Promise<void>((resolve) => {
      finish = resolve;
    });
    await page.route(endpoint, async (route) => {
      expect(route.request().postDataJSON()).toEqual({ question: 'Проверить связи' });
      await release;
      await route.fulfill({ json: { answer, sources: [source] } });
    });

    await page.goto('/assistant');
    const avatar = page.locator('.assistant-alexey[data-placed]');
    const pupils = avatar.locator('.assistant-alexey-pupils');
    await expect(avatar).toHaveAttribute('data-state', 'idle');
    await expect(avatar.locator('.assistant-alexey-art')).toHaveCSS(
      'animation-name',
      'alexey-float',
    );
    await expect(avatar.locator('.assistant-alexey-blink')).toHaveCSS(
      'animation-name',
      'alexey-blink',
    );

    const position = await avatar.boundingBox();
    if (!position) throw new Error('Алексей не отрисован');
    await page.mouse.move(position.x - 35, position.y + 45);
    await expect(pupils).toHaveAttribute('style', /translate\(-/);
    await page.mouse.move(position.x + position.width + 35, position.y + 45);
    await expect(pupils).toHaveAttribute('style', /translate\((?!-)/);

    const field = page.getByRole('textbox', { name: 'Вопрос ассистенту' });
    await field.fill('Проверить связи');
    await expect(avatar).toHaveAttribute('data-state', 'typing');
    await expect(pupils).toHaveAttribute('style', /translate\(/);
    await field.press('Enter');
    try {
      await expect(avatar).toHaveAttribute('data-state', 'waiting');
      const waiting = page.locator('.assistant-alexey-wait');
      await expect(waiting).toBeVisible();
      await expect
        .poll(async () => {
          const mascot = await avatar.boundingBox();
          const text = await waiting.boundingBox();
          return Boolean(mascot && text && mascot.x + mascot.width < text.x);
        })
        .toBe(true);
      await expect(page.getByRole('button', { name: 'Отправить' })).toBeDisabled();
    } finally {
      finish();
    }

    await expect(avatar).toHaveAttribute('data-state', 'speaking');
    const written = page.locator('.assistant-animated-turn .assistant-alexey-copy span');
    await expect(written).toHaveAttribute('aria-hidden', 'true');
    await expect.poll(async () => (await written.textContent())?.length ?? 0).toBeGreaterThan(0);
    expect(answer.startsWith((await written.textContent()) ?? '')).toBe(true);
    await expect(avatar.locator('.assistant-alexey-mouth')).not.toHaveAttribute('height', '3.5');
    await expect
      .poll(async () => {
        const mascot = await avatar.boundingBox();
        const text = await written.boundingBox();
        return Boolean(mascot && text && mascot.x + mascot.width < text.x);
      })
      .toBe(true);
    await expect(written).toHaveText(answer);
    await expect(avatar).toHaveAttribute('data-state', 'idle');
    await expect(page.getByRole('link', { name: source.label })).toHaveAttribute(
      'href',
      '/officials/example',
    );
    expect(await page.evaluate(() => document.documentElement.scrollWidth === innerWidth)).toBe(
      true,
    );
  });
}

test('Алексей сохраняет ошибки и полный ответ при уменьшенном движении', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  let attempts = 0;
  await page.route(endpoint, (route) =>
    ++attempts === 1
      ? route.fulfill({ status: 503, json: { detail: 'Ассистент недоступен' } })
      : route.fulfill({ json: { answer, sources: [source] } }),
  );
  await page.goto('/assistant');
  const avatar = page.locator('.assistant-alexey[data-placed]');
  await expect(avatar.locator('.assistant-alexey-art')).toHaveCSS('animation-name', 'none');
  const field = page.getByRole('textbox', { name: 'Вопрос ассистенту' });
  await field.fill('Первый вопрос');
  await page.getByRole('button', { name: 'Отправить' }).click();
  await expect(page.getByText(/Ошибка:.*Ассистент недоступен/)).toBeVisible();
  await field.fill('Повторить вопрос');
  await field.press('Enter');
  await expect(page.getByText(answer)).toBeVisible();
  await expect(page.getByRole('link', { name: source.label })).toBeVisible();
  await expect(avatar).toHaveAttribute('data-state', 'idle');
  await expect(avatar.locator('.assistant-alexey-mouth')).toHaveAttribute('height', '3.5');
});

test('Алексей краснеет при наборе мата и успокаивается после правки', async ({ page }) => {
  const question = 'Пиздец, проверь связи!';
  let sent: unknown;
  await page.route(endpoint, (route) => {
    sent = route.request().postDataJSON();
    return route.fulfill({ json: { answer, sources: [source] } });
  });
  await page.goto('/assistant');
  const avatar = page.locator('.assistant-alexey[data-placed]');
  const field = page.getByRole('textbox', { name: 'Вопрос ассистенту' });
  const cheeks = avatar.locator('.assistant-alexey-skin').last();

  await field.fill('Проверь требования к учебнику и договор страховки');
  await expect(avatar).not.toHaveAttribute('data-mood', 'annoyed');

  await field.fill('Проверь, ЁБАНЫЙ!');
  await expect(avatar).toHaveAttribute('data-state', 'typing');
  await expect(avatar).toHaveAttribute('data-mood', 'annoyed');
  await expect(cheeks).toHaveCSS('fill', 'rgb(244, 162, 156)');

  await field.fill('Проверь связи!');
  await expect(avatar).not.toHaveAttribute('data-mood', 'annoyed');
  await expect(cheeks).toHaveCSS('fill', 'rgb(167, 215, 238)');

  await field.fill(question);
  await expect(avatar).toHaveAttribute('data-mood', 'annoyed');
  await field.press('Enter');
  await expect.poll(() => sent).toEqual({ question });
  await expect(avatar).not.toHaveAttribute('data-mood', 'annoyed');
  await expect(page.getByText(answer, { exact: true })).toBeVisible();
});
