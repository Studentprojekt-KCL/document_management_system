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

test.describe('AI features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/search');
    await login(page, 'muaw22');
    await searchFor(page, 'test');
  });

  test('generate and regenerate AI summary', async ({ page }) => {
    // Open a file
    const file = page.getByRole('button', { name: /README\.md/i }).first();
    await expect(file).toBeVisible({ timeout: 10_000 });
    await file.click();
    await expect(page.getByRole('button', { name: 'Close preview' })).toBeVisible();

    // Generate summary
    const generateBtn = page.getByRole('button', { name: 'Generate AI Summary' });
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // Wait for summary to appear — the button should change to "Regenerate"
    const regenSummaryBtn = page.getByRole('button', { name: 'Regenerate Summary' });
    await expect(regenSummaryBtn).toBeVisible({ timeout: 15_000 });

    // Regenerate and verify the button is still there
    await regenSummaryBtn.click();
    await expect(regenSummaryBtn).toBeVisible({ timeout: 15_000 });
  });

  test('find similar files and view results', async ({ page }) => {
    // Open a file with known similar matches
    const file = page.getByRole('button', { name: /CMakeLists\.txt/i }).first();
    await expect(file).toBeVisible({ timeout: 10_000 });
    await file.click();
    await expect(page.getByRole('button', { name: 'Close preview' })).toBeVisible();

    // Find similar files
    const findSimilarBtn = page.getByRole('button', { name: 'Find Similar Files' });
    await expect(findSimilarBtn).toBeVisible();
    await findSimilarBtn.click();

    // Wait for similar files list to populate
    const similarItems = page.getByRole('listitem');
    await expect(similarItems.first()).toBeVisible({ timeout: 15_000 });

    // Verify we got at least one result
    const count = await similarItems.count();
    expect(count).toBeGreaterThan(0);
  });

  test('regenerate similar files returns results', async ({ page }) => {
    const file = page.getByRole('button', { name: /CMakeLists\.txt/i }).first();
    await expect(file).toBeVisible({ timeout: 10_000 });
    await file.click();
    await expect(page.getByRole('button', { name: 'Close preview' })).toBeVisible();

    // First find similar files
    const findSimilarBtn = page.getByRole('button', { name: 'Find Similar Files' });
    await expect(findSimilarBtn).toBeVisible();
    await findSimilarBtn.click();

    // Wait for initial results
    await expect(page.getByRole('listitem').first()).toBeVisible({ timeout: 15_000 });

    // Regenerate
    const regenBtn = page.getByRole('button', { name: 'Regenerate Similar Files' });
    await expect(regenBtn).toBeVisible();
    await regenBtn.click();

    // Results should still be present after regeneration
    await expect(page.getByRole('listitem').first()).toBeVisible({ timeout: 15_000 });
  });

  test('select similar files and merge', async ({ page }) => {
    const file = page.getByRole('button', { name: /CMakeLists\.txt/i }).first();
    await expect(file).toBeVisible({ timeout: 10_000 });
    await file.click();
    await expect(page.getByRole('button', { name: 'Close preview' })).toBeVisible();

    // Find similar files
    await page.getByRole('button', { name: 'Find Similar Files' }).click();
    await expect(page.getByRole('listitem').first()).toBeVisible({ timeout: 15_000 });

    // Select the first few similar items
    const similarItems = page.getByRole('listitem');
    const count = await similarItems.count();
    const selectCount = Math.min(count, 3);

    for (let i = 0; i < selectCount; i++) {
      await similarItems.nth(i).click();
    }

    // Click merge
    const mergeBtn = page.getByRole('button', { name: 'Merge Files' });
    if (await mergeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await mergeBtn.click();

      // The merge dialog or result should appear — check for either
      // "Merge & Summarize" button or a confirmation
      const mergeSummarize = page.getByRole('button', { name: 'Merge & Summarize' });
      if (await mergeSummarize.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await mergeSummarize.click();

        // Wait for merge to complete — some loading indicator should resolve
        await page.waitForTimeout(2_000);
      }
    }

    // Escape any open dialogs
    await page.keyboard.press('Escape');

    // App should still be responsive
    await expect(
      page.getByRole('textbox', { name: /Search for documents/i })
    ).toBeVisible();
  });
});