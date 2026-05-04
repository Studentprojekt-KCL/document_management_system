// @ts-check
/// <reference types="node" />
import { defineConfig, devices } from '@playwright/test';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  /* Global timeout per test — stress tests can be slow */
  timeout: 60_000,

  use: {
    baseURL: 'http://localhost:8080',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    /* Give actions a bit more room on slower dev machines */
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },

  /* Start with Chromium only; add more browsers when tests are stable */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Uncomment when ready to expand coverage:
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  /* Auto-start your dev server if not already running */
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:8080',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 30_000,
  // },
});