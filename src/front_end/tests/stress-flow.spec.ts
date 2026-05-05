import { test, expect, type Page } from '@playwright/test';

/* ═══════════════════════════════════════════════
   Shared helpers
   ═══════════════════════════════════════════════ */

async function goToLogin(page: Page) {
  const loginBtn = page.getByRole('button', { name: 'Go to login' });
  if (await loginBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await loginBtn.click();
  }
  await expect(
    page.getByRole('button', { name: 'Sign in with Microsoft Entra' })
  ).toBeVisible({ timeout: 10000 });
}

async function login(page: Page, user: string) {
  await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
  await page.getByRole('textbox', { name: 'Username or email' }).fill(user);
  await page.getByRole('textbox', { name: 'Password' }).fill('pass');
  await page.getByRole('button', { name: 'Sign In' }).click();

  await expect(
    page.getByRole('textbox', { name: /Search for documents/i })
  ).toBeVisible({ timeout: 10000 });
}

async function logout(page: Page) {
  const logoutBtn = page.getByRole('button', { name: 'Logout' });
  if (await logoutBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await logoutBtn.click();
    await page.waitForTimeout(500);
  }
}

async function searchFor(page: Page, query: string) {
  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
  await searchInput.fill(query);
  await page.getByRole('button', { name: /^Search$/ }).click();
  await expect(searchInput).not.toBeDisabled({ timeout: 10000 });
}

async function openFilePreview(page: Page, filePattern: RegExp) {
  const file = page.getByRole('button', { name: filePattern }).first();
  await expect(file).toBeVisible({ timeout: 10000 });
  await file.click();
  await expect(page.getByRole('button', { name: 'Close preview' })).toBeVisible();
}

async function closePreview(page: Page) {
  await page.getByRole('button', { name: 'Close preview' }).click();
  await page.waitForTimeout(300);
}

/* ═══════════════════════════════════════════════
   Console error capture
   ═══════════════════════════════════════════════ */

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];

  page.on('pageerror', (err) => {
    errors.push(`PAGE ERROR: ${err.message}`);
  });

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(`BROWSER ERROR: ${msg.text()}`);
    }
  });

  test.info().attach('browser-errors', {
    body: '',
    contentType: 'text/plain',
  });
});

function assertNoErrors(errors: string[]) {
  expect(errors, `Unexpected errors:\n${errors.join('\n')}`).toEqual([]);
}

/* ═══════════════════════════════════════════════
   Test: Aggressive stress flow
   ═══════════════════════════════════════════════ */

test('aggressive stress flow', async ({ page }) => {
  await page.goto('/search');
  await goToLogin(page);
  await login(page, 'muaw22');

  const editBtn = page.getByRole('button', { name: 'Edit' });

  // --- Search loop with file preview + edit spam ---
  for (let i = 0; i < 3; i++) {
    await searchFor(page, `test ${i}`);
    await openFilePreview(page, /CMakeLists.txt/i);

    await expect(editBtn).toBeVisible();

    for (let j = 0; j < 5; j++) {
      await editBtn.click();
      await page.waitForTimeout(100);
      await expect(editBtn).toBeVisible();
    }

    await expect(page.getByText('Security Class', { exact: true })).toBeVisible();
    await expect(page.getByText('File Size', { exact: true })).toBeVisible();

    await closePreview(page);
  }

  // --- AI actions on a different file ---
  await searchFor(page, 'golden_commands');

  const secondFile = page.getByRole('button', { name: /golden_commands.txt/i }).first();
  await expect(secondFile).toBeVisible({ timeout: 10000 });
  await secondFile.click();
  await expect(editBtn).toBeVisible();

  const aiButtons = ['Generate AI Summary', 'Find Similar Files'];

  for (const name of aiButtons) {
    const btn = page.getByRole('button', { name });
    if (await btn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await btn.click();
      await page.waitForTimeout(500);
    }
  }

  const regenBtn = page.getByRole('button', { name: 'Regenerate Similar Files' });
  if (await regenBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await regenBtn.click();
    await page.waitForTimeout(500);
  }

  const similarItems = page.getByRole('listitem');
  const count = await similarItems.count();
  for (let i = 0; i < Math.min(count, 5); i++) {
    await similarItems.nth(i).click();
  }

  const mergeBtn = page.getByRole('button', { name: 'Merge Files' });
  if (await mergeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await mergeBtn.click();
    const mergeSumBtn = page.getByRole('button', { name: 'Merge & Summarize' });
    if (await mergeSumBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await mergeSumBtn.click();
    }
  }

  await page.keyboard.press('Escape');

  // --- Settings stress toggling ---
  const securityTab = page.getByRole('button', { name: 'Security & Compliance' });
  if (await securityTab.isVisible({ timeout: 3000 }).catch(() => false)) {
    await securityTab.click();
  }

  const settingsTab = page.getByRole('button', { name: 'System Settings' });
  if (await settingsTab.isVisible({ timeout: 3000 }).catch(() => false)) {
    await settingsTab.click();
  }

  const toggles = [
    'Gitlab',
    'PDF (.pdf)',
    'Word (.docx, .doc, .odt)',
    'Text (.txt, .md)',
    'Excel (.xlsx, .ods)',
    'PowerPoint (.pptx, .ppt, .odp)',
    'Public',
    'Internal',
    'Sensitive',
    'Confidential',
  ];

  for (let round = 0; round < 2; round++) {
    for (const name of toggles) {
      const btn = page.getByRole('button', { name, exact: true });
      if (await btn.isVisible().catch(() => false)) {
        await btn.click();
        await page.waitForTimeout(50);
      }
    }
  }

  const clearBtn = page.getByRole('button', { name: 'Clear all' });
  if (await clearBtn.isVisible().catch(() => false)) {
    await clearBtn.click();
  }

  // --- Notification toggle ---
  const notifications = page.getByRole('button', { name: 'Notifications' });
  if (await notifications.isVisible().catch(() => false)) {
    for (let i = 0; i < 3; i++) {
      await notifications.click();
      await page.waitForTimeout(100);
    }
  }

  // --- Logout and switch user ---
  await logout(page);
  await login(page, 'osoh22');

  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });

  for (let i = 0; i < 2; i++) {
    await searchInput.fill('test');
    await page.getByRole('button', { name: /^Search$/ }).click();
    await expect(searchInput).not.toBeDisabled({ timeout: 10000 });

    await openFilePreview(page, /CMakeLists.txt/i);
    await expect(page.getByText('Security Class', { exact: true })).toBeVisible();
    await closePreview(page);
  }

  await logout(page);
});

/* ═══════════════════════════════════════════════
   Test: Rapid search + preview open/close cycles
   ═══════════════════════════════════════════════ */

test('rapid search and preview cycles', async ({ page }) => {
  await page.goto('/search');
  await goToLogin(page);
  await login(page, 'muaw22');

  const queries = ['test', 'CMake', 'config', 'readme', 'golden'];
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  // 20 iterations of search + open + close
  for (let i = 0; i < 20; i++) {
    const q = queries[i % queries.length];
    await searchFor(page, `${q} ${i}`);
    await page.waitForTimeout(200);

    // Try to open any visible file
    const fileBtn = page.getByRole('button', { name: /.*/ }).first();
    if (await fileBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await fileBtn.click();
      await page.waitForTimeout(200);
      // Close via escape or button
      await page.keyboard.press('Escape');
      await page.waitForTimeout(150);
    }
  }

  // Search bar should still work
  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
  await expect(searchInput).toBeVisible();
  await expect(searchInput).not.toBeDisabled();

  assertNoErrors(errors);
});

/* ═══════════════════════════════════════════════
   Test: Rapid login / logout cycles
   ═══════════════════════════════════════════════ */

test('rapid login logout cycles', async ({ page }) => {
  const users = ['muaw22', 'osoh22'];
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  for (let round = 0; round < 3; round++) {
    for (const user of users) {
      await page.goto('/search');
      await goToLogin(page);
      await login(page, user);

      // Quick smoke check after login
      const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
      await expect(searchInput).toBeVisible({ timeout: 5000 });

      await logout(page);
      await page.waitForTimeout(500);
    }
  }

  assertNoErrors(errors);
});

/* ═══════════════════════════════════════════════
   Test: Rapid filter toggle bursts
   ═══════════════════════════════════════════════ */

test('rapid filter toggle bursts', async ({ page }) => {
  await page.goto('/search');
  await goToLogin(page);
  await login(page, 'muaw22');

  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  // Open settings/security panel first
  const settingsTab = page.getByRole('button', { name: 'System Settings' });
  if (await settingsTab.isVisible({ timeout: 3000 }).catch(() => false)) {
    await settingsTab.click();
  }

  const filterNames = [
    'PDF (.pdf)',
    'Word (.docx, .doc, .odt)',
    'Text (.txt, .md)',
    'Excel (.xlsx, .ods)',
    'PowerPoint (.pptx, .ppt, .odp)',
    'Public',
    'Internal',
    'Sensitive',
    'Confidential',
  ];

  // 5 rounds of rapid toggle on/off
  for (let round = 0; round < 5; round++) {
    for (const name of filterNames) {
      const btn = page.getByRole('button', { name, exact: true });
      if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await btn.click();
      }
    }
  }

  // Clear all at the end
  const clearBtn = page.getByRole('button', { name: 'Clear all' });
  if (await clearBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await clearBtn.click();
  }

  // Page should still be functional
  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
  await expect(searchInput).toBeVisible();

  assertNoErrors(errors);
});

/* ═══════════════════════════════════════════════
   Test: Rapid edit spam on file preview
   ═══════════════════════════════════════════════ */

test('rapid edit spam on file preview', async ({ page }) => {
  await page.goto('/search');
  await goToLogin(page);
  await login(page, 'muaw22');

  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  await searchFor(page, 'CMakeLists');
  await openFilePreview(page, /CMakeLists.txt/i);

  const editBtn = page.getByRole('button', { name: 'Edit' });
  await expect(editBtn).toBeVisible();

  // 20 rapid edit clicks
  for (let i = 0; i < 20; i++) {
    await editBtn.click();
    await page.waitForTimeout(50);
  }

  // UI should still be intact
  await expect(editBtn).toBeVisible();
  await expect(page.getByText('Security Class', { exact: true })).toBeVisible();
  await expect(page.getByText('File Size', { exact: true })).toBeVisible();

  await closePreview(page);

  assertNoErrors(errors);
});
