import { test, expect } from '@playwright/test';

/**
 * Smoke tests — quick sanity checks that the app loads and core flows work.
 * These should pass in under 30 seconds.
 */

test.describe('smoke tests', () => {
  test('app loads and shows login entry point', async ({ page }) => {
    await page.goto('/search');

    // The landing page should have a way to reach login
    const loginBtn = page.getByRole('button', { name: 'Go to login' });
    await expect(loginBtn).toBeVisible({ timeout: 10_000 });
  });

  test('login flow reaches search page', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('button', { name: 'Go to login' }).click();
    await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
    await page.getByRole('textbox', { name: 'Username or email' }).fill('muaw22');
    await page.getByRole('textbox', { name: 'Password' }).fill('pass');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(
      page.getByRole('textbox', { name: /Search for documents/i })
    ).toBeVisible({ timeout: 10_000 });
  });

  test('search returns results and opens preview', async ({ page }) => {
    await page.goto('/');

    // Login
    await page.getByRole('button', { name: 'Go to login' }).click();
    await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
    await page.getByRole('textbox', { name: 'Username or email' }).fill('muaw22');
    await page.getByRole('textbox', { name: 'Password' }).fill('pass');
    await page.getByRole('button', { name: 'Sign In' }).click();

    const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
    await expect(searchInput).toBeVisible({ timeout: 10_000 });

    // Perform a search
    await searchInput.fill('test');
    await page.getByRole('button', { name: /^Search$/ }).click();

    // Wait for results
    const file = page.getByRole('button', { name: /CMakeLists.txt/i });
    await expect(file).toBeVisible({ timeout: 10_000 });

    // Open preview and verify metadata
    await file.click();
    await expect(page.getByText(/Security Class/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Close preview' })).toBeVisible();

    // Close preview
    await page.getByRole('button', { name: 'Close preview' }).click();
  });

  test('logout returns to landing', async ({ page }) => {
    await page.goto('/');

    // Login
    await page.getByRole('button', { name: 'Go to login' }).click();
    await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
    await page.getByRole('textbox', { name: 'Username or email' }).fill('muaw22');
    await page.getByRole('textbox', { name: 'Password' }).fill('pass');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(
      page.getByRole('textbox', { name: /Search for documents/i })
    ).toBeVisible({ timeout: 10_000 });

    // Logout
    await page.getByRole('button', { name: 'Logout' }).click();

    // Should be back at the landing/login entry
    await expect(
      page.getByRole('button', { name: 'Go to login' })
    ).toBeVisible({ timeout: 10_000 });
  });
});