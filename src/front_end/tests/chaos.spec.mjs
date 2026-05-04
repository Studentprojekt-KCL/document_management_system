import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  page.on('pageerror', (err) => {
    console.log('PAGE ERROR:', err.message);
  });

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.log('BROWSER ERROR:', msg.text());
    }
  });
});

/**
 * Chaotic user test — simulates unpredictable navigation and clicks.
 * Asserts: no uncaught exceptions (pageerror) and the page remains responsive.
 */
test('chaotic user does not crash the app', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (err) => errors.push(err.message));

  await page.goto('/');

  // First, log in so we're actually inside the app
  const loginBtn = page.getByRole('button', { name: 'Go to login' });
  if (await loginBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await loginBtn.click();
    await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
    await page.getByRole('textbox', { name: 'Username or email' }).fill('muaw22');
    await page.getByRole('textbox', { name: 'Password' }).fill('pass');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(
      page.getByRole('textbox', { name: /Search for documents/i })
    ).toBeVisible({ timeout: 10_000 });
  }

  // Controlled random actions — each wrapped in try/catch so one
  // failure doesn't abort the chaos run
  const actions = [
    async () => {
      // Random click somewhere on the page
      const viewportSize = page.viewportSize();
      if (!viewportSize) return;
      const { width, height } = viewportSize;
      await page.mouse.click(
        Math.floor(Math.random() * width),
        Math.floor(Math.random() * height)
      );
    },
    async () => {
      // Type a random search query
      const input = page.getByRole('textbox', { name: /Search for documents/i });
      if (await input.isVisible().catch(() => false)) {
        await input.fill(`chaos-${Math.random().toString(36).slice(2, 8)}`);
        await page.getByRole('button', { name: /^Search$/ }).click();
      }
    },
    async () => {
      // Press Escape (close any open modals/drawers)
      await page.keyboard.press('Escape');
    },
    async () => {
      // Click a random visible button
      const buttons = page.getByRole('button');
      const count = await buttons.count();
      if (count > 0) {
        const idx = Math.floor(Math.random() * count);
        const btn = buttons.nth(idx);
        if (await btn.isVisible().catch(() => false)) {
          await btn.click();
        }
      }
    },
    async () => {
      // Navigate back/forward
      await page.goBack().catch(() => {});
    },
    async () => {
      await page.goForward().catch(() => {});
    },
  ];

  for (let i = 0; i < 30; i++) {
    const action = actions[Math.floor(Math.random() * actions.length)];
    try {
      await action();
      // Small pause so the app can settle
      await page.waitForTimeout(200);
    } catch {
      // Swallow action-level errors — we're testing that the *app* doesn't crash
    }
  }

  // Final assertion: no unhandled JS exceptions occurred
  expect(errors).toEqual([]);

  // The page should still be responsive — check we can navigate home
  await page.goto('/');
  await expect(page.locator('body')).toBeVisible();
});