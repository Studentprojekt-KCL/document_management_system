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

/* ─── Tests ─── */

test.describe('search filters', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/search');
    await login(page, 'muaw22');
    await searchFor(page, 'test');
  });

  test('document-only toggle filters results', async ({ page }) => {
    const toggleBtn = page.getByRole('button', { name: 'Showing Documents Only' });

    // Toggle to "Documents Only"
    await toggleBtn.click();
    await expect(toggleBtn).toBeVisible();

    // Toggle back to "All Files"
    await toggleBtn.click();
    const allFilesBtn = page.getByRole('button', { name: 'Showing All Files' });
    await expect(allFilesBtn).toBeVisible();

    // Toggle again to confirm it switches back
    await allFilesBtn.click();
    await expect(page.getByRole('button', { name: 'Showing Documents Only' })).toBeVisible();
  });

  test('source system filters toggle on and off', async ({ page }) => {
    const sources = ['Gitlab', 'SMB'];

    for (const name of sources) {
      const btn = page.getByRole('button', { name, exact: true });
      await expect(btn).toBeVisible();

      // Toggle on
      await btn.click();
      await page.waitForTimeout(100);

      // Toggle off
      await btn.click();
      await page.waitForTimeout(100);
    }

    // Results should still be visible after toggling
    await expect(
      page.getByRole('button', { name: /\.txt|\.md|\.pdf/i }).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('file type filters toggle on and off', async ({ page }) => {
    const fileTypes = [
      'PDF (.pdf)',
      'Word (.docx, .doc, .odt)',
      'Text (.txt, .md)',
      'Excel (.xlsx, .ods)',
      'PowerPoint (.pptx, .ppt, .odp)',
    ];

    for (const name of fileTypes) {
      const btn = page.getByRole('button', { name });
      await expect(btn).toBeVisible();

      await btn.click();
      await page.waitForTimeout(100);

      await btn.click();
      await page.waitForTimeout(100);
    }

    // Results should still be visible
    await expect(
      page.getByRole('button', { name: /\.txt|\.md|\.pdf/i }).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('security classification filters toggle on and off', async ({ page }) => {
    const classifications = ['Public', 'Internal', 'Sensitive', 'Confidential', 'Pending'];

    for (const name of classifications) {
      const btn = page.getByRole('button', { name, exact: true });
      await expect(btn).toBeVisible();

      await btn.click();
      await page.waitForTimeout(100);

      await btn.click();
      await page.waitForTimeout(100);
    }
  });

  test('multiple filters can be active then cleared', async ({ page }) => {
    // Activate several filters
    const filtersToActivate = [
      'Gitlab',
      'Word (.docx, .doc, .odt)',
      'Text (.txt, .md)',
      'Confidential',
      'Sensitive',
      'Internal',
    ];

    for (const name of filtersToActivate) {
      const btn = page.getByRole('button', { name, exact: true });
      if (await btn.isVisible().catch(() => false)) {
        await btn.click();
        await page.waitForTimeout(100);
      }
    }

    // Clear all filters
    const clearBtn = page.getByRole('button', { name: 'Clear all' });
    await expect(clearBtn).toBeVisible();
    await clearBtn.click();

    // After clearing, results should reload — verify at least one result is visible
    await expect(
      page.getByRole('button', { name: /\.txt|\.md|\.pdf/i }).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});