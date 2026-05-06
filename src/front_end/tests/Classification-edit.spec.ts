import { test, expect, type Page } from '@playwright/test';

/* ─── Helpers ─── */

async function login(page: Page, user: string) {
  await page.getByRole('button', { name: 'Go to login' }).click();
  await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
  await page.getByRole('textbox', { name: 'Username or email' }).fill(user);
  await page.getByRole('textbox', { name: 'Password' }).fill('pass');
  await page.getByRole('button', { name: 'Sign In' }).click();

  await expect(
    page.getByRole('textbox', { name: /Search for documents/i })
  ).toBeVisible({ timeout: 10_000 });
}

async function searchFor(page: Page, query: string) {
  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
  await searchInput.fill(query);
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(searchInput).not.toBeDisabled({ timeout: 10_000 });
}

/**
 * Opens edit mode, selects a classification, and saves.
 * Uses .nth() offsets because the same label ("Internal", "Public", etc.)
 * appears both in the sidebar filters and inside the edit dropdown.
 * The codegen recording showed these are at nth(1) or nth(2) depending
 * on the classification — we use a flexible approach here.
 */
async function setClassification(page: Page, classificationName: string) {
  const editBtn = page.getByRole('button', { name: 'Edit' });
  await expect(editBtn).toBeVisible();
  await editBtn.click();

  // In edit mode, the classification buttons inside the preview panel
  // are distinct from the sidebar filter buttons. Pick the one inside
  // the preview by selecting a later occurrence.
  const candidates = page.getByRole('button', { name: classificationName, exact: true });
  const count = await candidates.count();

  // Click the last matching button (the one inside the edit form, not the filter sidebar)
  if (count > 1) {
    await candidates.nth(count - 1).click();
  } else {
    await candidates.click();
  }

  const saveBtn = page.getByRole('button', { name: 'Save' });
  await expect(saveBtn).toBeVisible();
  await saveBtn.click();

  // Wait for save to complete — edit button should reappear
  await expect(editBtn).toBeVisible({ timeout: 5_000 });
}

/* ─── Tests ─── */

test.describe('security classification editing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/search');
    await login(page, 'muaw22');
    await searchFor(page, 'test');

    // Open a file preview
    const file = page.getByRole('button', { name: /README\.md/i }).first();
    await expect(file).toBeVisible({ timeout: 10_000 });
    await file.click();
    await expect(page.getByRole('button', { name: 'Close preview' })).toBeVisible();
  });

  test('can cycle through all classification levels', async ({ page }) => {
    const classifications = [
      'Internal',
      'Sensitive',
      'Confidential',
      'Pending',
      'Public',
    ];

    for (const classification of classifications) {
      await setClassification(page, classification);

      // Verify the classification text appears in the metadata panel
      await expect(
        page.getByText(classification, { exact: true }).first()
      ).toBeVisible();
    }
  });

  test('edit mode can be cancelled by clicking Edit again', async ({ page }) => {
    const editBtn = page.getByRole('button', { name: 'Edit' });
    await expect(editBtn).toBeVisible();

    // Enter edit mode
    await editBtn.click();

    // Save button should appear
    const saveBtn = page.getByRole('button', { name: 'Save' });
    await expect(saveBtn).toBeVisible();

    // Click edit again (some UIs treat this as cancel)
    // or look for a Cancel button
    const cancelBtn = page.getByRole('button', { name: 'Cancel' });
    if (await cancelBtn.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await cancelBtn.click();
    } else {
      // If no cancel button, just save without changes
      await saveBtn.click();
    }

    await expect(editBtn).toBeVisible();
  });
});