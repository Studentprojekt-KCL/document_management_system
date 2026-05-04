import { test, expect, type Page } from '@playwright/test';

/**
 * Smoke tests — quick sanity checks that the app loads and core flows work.
 * These should pass in under 30 seconds.
 */

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

test.describe('smoke tests', () => {
  test('app loads and shows login entry point', async ({ page }) => {
    await page.goto('/search');

    const loginBtn = page.getByRole('button', { name: 'Go to login' });
    await expect(loginBtn).toBeVisible({ timeout: 10_000 });
  });

  test('login flow reaches search page', async ({ page }) => {
    await page.goto('/search');
    await login(page, 'muaw22');

    await expect(
      page.getByRole('textbox', { name: /Search for documents/i })
    ).toBeVisible();
  });

  test('search returns results and opens preview', async ({ page }) => {
    await page.goto('/search');
    await login(page, 'muaw22');

    const searchInput = page.getByRole('textbox', { name: /Search for documents/i });

    await searchInput.fill('test');
    await page.getByRole('button', { name: /^Search$/ }).click();

    // Use .first() — CMakeLists.txt matches multiple entries (Public + Internal)
    const file = page.getByRole('button', { name: /CMakeLists.txt/i }).first();
    await expect(file).toBeVisible({ timeout: 10_000 });

    await file.click();
    await expect(page.getByText('Security Class', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Close preview' })).toBeVisible();

    await page.getByRole('button', { name: 'Close preview' }).click();
  });

  test('logout returns to login screen', async ({ page }) => {
    await page.goto('/search');
    await login(page, 'muaw22');

    await page.getByRole('button', { name: 'Logout' }).click();

    // After logout the app redirects to the Keycloak login screen
    await expect(
      page.getByRole('button', { name: 'Sign in with Microsoft Entra ID' })
    ).toBeVisible({ timeout: 10_000 });
  });
});