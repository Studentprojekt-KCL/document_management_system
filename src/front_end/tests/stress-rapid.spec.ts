import { test, expect, type Page } from '@playwright/test';

/* ═══════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════ */

async function login(page: Page, user: string) {
  const loginBtn = page.getByRole('button', { name: 'Go to login' });
  if (await loginBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await loginBtn.click();
  }
  await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
  await page.getByRole('textbox', { name: 'Username or email' }).fill(user);
  await page.getByRole('textbox', { name: 'Password' }).fill('pass');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(
    page.getByRole('textbox', { name: /Search for documents/i })
  ).toBeVisible({ timeout: 10000 });
}

async function searchFor(page: Page, query: string) {
  const input = page.getByRole('textbox', { name: /Search for documents/i });
  await input.fill(query);
  await page.getByRole('button', { name: /^Search$/ }).click();
  await expect(input).not.toBeDisabled({ timeout: 10000 });
}

function captureErrors(page: Page) {
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(`PAGE: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`CONSOLE: ${msg.text()}`);
  });
  return errors;
}

function assertNoErrors(errors: string[]) {
  expect(errors, `Errors detected:\n${errors.join('\n')}`).toEqual([]);
}

/* ═══════════════════════════════════════════════
   Test: Rapid repeated searches
   ═══════════════════════════════════════════════ */

test('rapid repeated searches', async ({ page }) => {
  await page.goto('/search');
  await login(page, 'muaw22');

  const errors = captureErrors(page);

  const queries = Array.from({ length: 30 }, (_, i) => `query-${i}-${Math.random().toString(36).slice(2, 6)}`);

  for (const q of queries) {
    await searchFor(page, q);
    await page.waitForTimeout(100);
  }

  // Search input should still be functional
  const input = page.getByRole('textbox', { name: /Search for documents/i });
  await expect(input).toBeVisible();
  await expect(input).not.toBeDisabled();

  assertNoErrors(errors);
});

/* ═══════════════════════════════════════════════
   Test: Rapid modal open/close
   ═══════════════════════════════════════════════ */

test('rapid modal open close', async ({ page }) => {
  await page.goto('/search');
  await login(page, 'muaw22');

  const errors = captureErrors(page);

  await searchFor(page, 'CMakeLists');

  for (let i = 0; i < 15; i++) {
    // Open a file preview
    const fileBtn = page.getByRole('button', { name: /CMakeLists/i }).first();
    if (await fileBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await fileBtn.click();
      await page.waitForTimeout(100);
    }
    // Close immediately
    await page.keyboard.press('Escape');
    await page.waitForTimeout(100);
  }

  // UI should still render properly
  await expect(page.locator('body')).toBeVisible();
  assertNoErrors(errors);
});

/* ═══════════════════════════════════════════════
   Test: Concurrent-feeling rapid button clicks
   ═══════════════════════════════════════════════ */

test('rapid button click bursts', async ({ page }) => {
  await page.goto('/search');
  await login(page, 'muaw22');

  const errors = captureErrors(page);

  await searchFor(page, 'test');
  await page.waitForTimeout(300);

  // Click all visible buttons rapidly
  for (let round = 0; round < 3; round++) {
    const buttons = page.getByRole('button');
    const count = await buttons.count();
    for (let i = 0; i < Math.min(count, 20); i++) {
      const btn = buttons.nth(i);
      if (await btn.isVisible({ timeout: 500 }).catch(() => false)) {
        await btn.click();
        await page.waitForTimeout(30);
      }
    }
    await page.keyboard.press('Escape');
    await page.waitForTimeout(200);
  }

  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
  await expect(searchInput).toBeVisible();
  assertNoErrors(errors);
});

/* ═══════════════════════════════════════════════
   Test: Navigation stress
   ═══════════════════════════════════════════════ */

test('navigation stress', async ({ page }) => {
  await page.goto('/search');
  await login(page, 'muaw22');

  const errors = captureErrors(page);

  const routes = ['/', '/search', '/search?q=test', '/'];

  for (let round = 0; round < 5; round++) {
    for (const route of routes) {
      await page.goto(route);
      await page.waitForTimeout(200);
    }
    // Use browser back/forward
    await page.goBack().catch(() => {});
    await page.waitForTimeout(100);
    await page.goForward().catch(() => {});
    await page.waitForTimeout(100);
  }

  await expect(page.locator('body')).toBeVisible();
  assertNoErrors(errors);
});

/* ═══════════════════════════════════════════════
   Test: Keyboard input stress
   ═══════════════════════════════════════════════ */

test('keyboard input stress', async ({ page }) => {
  await page.goto('/search');
  await login(page, 'muaw22');

  const errors = captureErrors(page);

  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });

  // Rapid typing and clearing
  for (let i = 0; i < 20; i++) {
    await searchInput.fill(`stress-test-${i}-${'x'.repeat(i)}`);
    await page.waitForTimeout(50);
    await searchInput.fill('');
    await page.waitForTimeout(50);
  }

  // Special keys
  const specialKeys = ['Enter', 'Escape', 'Tab', 'ArrowDown', 'ArrowUp', 'Delete', 'Backspace'];
  for (const key of specialKeys) {
    for (let i = 0; i < 5; i++) {
      await searchInput.press(key);
      await page.waitForTimeout(50);
    }
  }

  await expect(searchInput).toBeVisible();
  assertNoErrors(errors);
});

/* ═══════════════════════════════════════════════
   Test: Resize and viewport stress
   ═══════════════════════════════════════════════ */

test('viewport resize stress', async ({ page }) => {
  await page.goto('/search');
  await login(page, 'muaw22');

  const errors = captureErrors(page);

  const sizes = [
    { width: 375, height: 812 },   // mobile
    { width: 768, height: 1024 },  // tablet
    { width: 1920, height: 1080 }, // desktop
    { width: 1280, height: 720 },  // laptop
  ];

  for (let round = 0; round < 3; round++) {
    for (const size of sizes) {
      await page.setViewportSize(size);
      await page.waitForTimeout(200);
    }
  }

  // Reset to default
  await page.setViewportSize({ width: 1280, height: 720 });
  await expect(page.locator('body')).toBeVisible();
  assertNoErrors(errors);
});

/* ═══════════════════════════════════════════════
   Test: AI action spam
   ═══════════════════════════════════════════════ */

test('ai action spam', async ({ page }) => {
  await page.goto('/search');
  await login(page, 'muaw22');

  const errors = captureErrors(page);

  await searchFor(page, 'golden_commands');

  const fileBtn = page.getByRole('button', { name: /golden_commands.txt/i }).first();
  if (await fileBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
    await fileBtn.click();
    await page.waitForTimeout(300);
  }

  // Spam AI-related buttons if they exist
  const aiButtonNames = [
    'Generate AI Summary',
    'Find Similar Files',
    'Regenerate Similar Files',
  ];

  for (let round = 0; round < 3; round++) {
    for (const name of aiButtonNames) {
      const btn = page.getByRole('button', { name });
      if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await btn.click();
        await page.waitForTimeout(100);
      }
    }
  }

  await page.keyboard.press('Escape');

  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
  await expect(searchInput).toBeVisible();
  assertNoErrors(errors);
});
