import { test, expect, type Page } from '@playwright/test';

/* ─── Shared helpers ─── */

async function login(page: Page, user: string) {
  await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
  await page.getByRole('textbox', { name: 'Username or email' }).fill(user);
  await page.getByRole('textbox', { name: 'Password' }).fill('pass');
  await page.getByRole('button', { name: 'Sign In' }).click();

  // Wait for the search page to fully load after login
  await expect(
    page.getByRole('textbox', { name: /Search for documents/i })
  ).toBeVisible({ timeout: 10_000 });
}

async function searchFor(page: Page, query: string) {
  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
  await searchInput.fill(query);
  await page.getByRole('button', { name: /^Search$/ }).click();
  // Wait for results to appear or loading to finish
  await expect(searchInput).not.toBeDisabled({ timeout: 10_000 });
}

async function openFilePreview(page: Page, filePattern: RegExp) {
  const file = page.getByRole('button', { name: filePattern }).first();
  await expect(file).toBeVisible({ timeout: 10_000 });
  await file.click();
  // Wait for the preview drawer to open
  await expect(page.getByRole('button', { name: 'Close preview' })).toBeVisible();
}

async function closePreview(page: Page) {
  await page.getByRole('button', { name: 'Close preview' }).click();
  // Small pause to let the drawer animate closed
  await page.waitForTimeout(300);
}

/* ─── Console error capture ─── */

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

  // Attach errors to test info for debugging on failure
  test.info().attach('browser-errors', {
    body: '', // placeholder, actual content added in afterEach if needed
    contentType: 'text/plain',
  });
});

/* ═══════════════════════════════════════════════
   Test: Aggressive stress flow
   ═══════════════════════════════════════════════ */

test('aggressive stress flow', async ({ page }) => {
  await page.goto('/search');

  // Navigate to login
  await page.getByRole('button', { name: 'Go to login' }).click();
  await login(page, 'muaw22');

  const editBtn = page.getByRole('button', { name: 'Edit' });

  // --- Search loop with file preview + edit spam ---
  for (let i = 0; i < 3; i++) {
    await searchFor(page, `test ${i}`);
    await openFilePreview(page, /CMakeLists.txt/i);

    await expect(editBtn).toBeVisible();

    // Rapid edit clicks — verify UI survives each one
    for (let j = 0; j < 5; j++) {
      await editBtn.click();
      // Small pause to let any transition settle
      await page.waitForTimeout(100);
      await expect(editBtn).toBeVisible();
    }

    // Validate metadata is still rendered
    await expect(page.getByText('Security Class', { exact: true })).toBeVisible();
    await expect(page.getByText('File Size', { exact: true })).toBeVisible();

    await closePreview(page);
  }

  // --- AI actions on a different file ---
  await searchFor(page, 'golden_commands');

  const secondFile = page.getByRole('button', { name: /golden_commands.txt/i }).first();
  await expect(secondFile).toBeVisible({ timeout: 10_000 });
  await secondFile.click();
  await expect(editBtn).toBeVisible();

  const aiButtons = [
    'Generate AI Summary',
    'Find Similar Files',
  ];

  for (const name of aiButtons) {
    const btn = page.getByRole('button', { name });
    if (await btn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await btn.click();
      // Give async AI operations time to respond
      await page.waitForTimeout(500);
    }
  }

  // Regenerate only makes sense after "Find Similar Files"
  const regenBtn = page.getByRole('button', { name: 'Regenerate Similar Files' });
  if (await regenBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await regenBtn.click();
    await page.waitForTimeout(500);
  }

  // --- Similar file selection (if any appeared) ---
  const similarItems = page.getByRole('listitem');
  const count = await similarItems.count();

  for (let i = 0; i < Math.min(count, 5); i++) {
    await similarItems.nth(i).click();
  }

  // Merge actions — only if buttons exist
  const mergeBtn = page.getByRole('button', { name: 'Merge Files' });
  if (await mergeBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await mergeBtn.click();

    const mergeSumBtn = page.getByRole('button', { name: 'Merge & Summarize' });
    if (await mergeSumBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await mergeSumBtn.click();
    }
  }

  await page.keyboard.press('Escape');

  // --- Settings stress toggling ---
  const securityTab = page.getByRole('button', { name: 'Security & Compliance' });
  if (await securityTab.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await securityTab.click();
  }

  const settingsTab = page.getByRole('button', { name: 'System Settings' });
  if (await settingsTab.isVisible({ timeout: 3_000 }).catch(() => false)) {
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
        await page.waitForTimeout(50); // tiny pause between rapid toggles
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
  await page.getByRole('button', { name: 'Logout' }).click();
  await login(page, 'osoh22');

  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });

  // --- Final validation as second user ---
  for (let i = 0; i < 2; i++) {
    await searchInput.fill('test');
    await page.getByRole('button', { name: /^Search$/ }).click();
    await expect(searchInput).not.toBeDisabled({ timeout: 10_000 });

    await openFilePreview(page, /CMakeLists.txt/i);
    await expect(page.getByText('Security Class', { exact: true })).toBeVisible();
    await closePreview(page);
  }

  await page.getByRole('button', { name: 'Logout' }).click();
});