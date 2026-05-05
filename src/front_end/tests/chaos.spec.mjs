import { test, expect } from '@playwright/test';

/* ═══════════════════════════════════════════════
   Seeded PRNG (mulberry32) for reproducibility
   ═══════════════════════════════════════════════ */

function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const SEED = process.env.CHAOS_SEED
  ? parseInt(process.env.CHAOS_SEED, 10)
  : Math.floor(Math.random() * 1e9);

/* ═══════════════════════════════════════════════
   Chaos action library — reusable helpers
   ═══════════════════════════════════════════════ */

function buildChaosActions(page, rng) {
  return [
    // 0: Random click anywhere on the page
    async () => {
      const viewport = page.viewportSize();
      if (!viewport) return;
      await page.mouse.click(
        Math.floor(rng() * viewport.width),
        Math.floor(rng() * viewport.height)
      );
    },

    // 1: Random search query
    async () => {
      const input = page.getByRole('textbox', { name: /Search for documents/i });
      if (await input.isVisible().catch(() => false)) {
        await input.fill(`chaos-${Math.floor(rng() * 1e6).toString(36)}`);
        const btn = page.getByRole('button', { name: /^Search$/ });
        if (await btn.isVisible().catch(() => false)) await btn.click();
      }
    },

    // 2: Press Escape (close modals/drawers)
    async () => {
      await page.keyboard.press('Escape');
    },

    // 3: Click a random visible button
    async () => {
      const buttons = page.getByRole('button');
      const count = await buttons.count();
      if (count > 0) {
        const btn = buttons.nth(Math.floor(rng() * count));
        if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
          await btn.click();
        }
      }
    },

    // 4: Navigate back
    async () => {
      await page.goBack().catch(() => {});
    },

    // 5: Navigate forward
    async () => {
      await page.goForward().catch(() => {});
    },

    // 6: Type random text into any visible input
    async () => {
      const inputs = page.locator('input:visible, textarea:visible');
      const count = await inputs.count();
      if (count > 0) {
        const input = inputs.nth(Math.floor(rng() * count));
        await input.fill(rng().toString(36).slice(2, 12));
      }
    },

    // 7: Rapid scroll up and down
    async () => {
      await page.evaluate((r) => {
        window.scrollBy(0, (r - 0.5) * 2000);
      }, rng());
    },

    // 8: Open/close the preview drawer if a file is visible
    async () => {
      const fileBtn = page
        .getByRole('button', { name: /.*/ })
        .first();
      if (await fileBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await fileBtn.click();
        await page.waitForTimeout(200);
        await page.keyboard.press('Escape');
      }
    },

    // 9: Toggle a random filter/checkbox if available
    async () => {
      const toggles = page.locator('[role="checkbox"]:visible, [role="switch"]:visible');
      const count = await toggles.count();
      if (count > 0) {
        await toggles.nth(Math.floor(rng() * count)).click();
      }
    },

    // 10: Double-click a random visible element
    async () => {
      const els = page.locator(':visible');
      const count = await els.count();
      if (count > 0) {
        const el = els.nth(Math.floor(rng() * Math.min(count, 50)));
        await el.dblclick().catch(() => {});
      }
    },

    // 11: Press random navigation keys
    async () => {
      const keys = ['Tab', 'Enter', 'ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End'];
      await page.keyboard.press(keys[Math.floor(rng() * keys.length)]);
    },

    // 12: Select random text and copy
    async () => {
      await page.evaluate(() => {
        const sel = window.getSelection();
        if (sel && document.body) {
          const range = document.createRange();
          range.selectNodeContents(document.body);
          sel.removeAllRanges();
          sel.addRange(range);
        }
      });
      await page.keyboard.press('Control+C');
    },

    // 13: Hover over a random visible link or button
    async () => {
      const targets = page.locator('a:visible, button:visible');
      const count = await targets.count();
      if (count > 0) {
        const el = targets.nth(Math.floor(rng() * count));
        const box = await el.boundingBox().catch(() => null);
        if (box) {
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        }
      }
    },

    // 14: Right-click context menu
    async () => {
      const viewport = page.viewportSize();
      if (!viewport) return;
      await page.mouse.click(
        Math.floor(rng() * viewport.width * 0.8),
        Math.floor(rng() * viewport.height * 0.8),
        { button: 'right' }
      );
      await page.keyboard.press('Escape'); // dismiss context menu
    },
  ];
}

/* ═══════════════════════════════════════════════
   Login helper
   ═══════════════════════════════════════════════ */

async function tryLogin(page) {
  const loginBtn = page.getByRole('button', { name: 'Go to login' });
  if (await loginBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await loginBtn.click();
    await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
    await page.getByRole('textbox', { name: 'Username or email' }).fill('muaw22');
    await page.getByRole('textbox', { name: 'Password' }).fill('pass');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(
      page.getByRole('textbox', { name: /Search for documents/i })
    ).toBeVisible({ timeout: 10000 });
  }
}

/* ═══════════════════════════════════════════════
   Test: chaotic user does not crash the app
   ═══════════════════════════════════════════════ */

test('chaotic user does not crash the app', async ({ page }) => {
  const errors = [];
  const actionLog = [];

  page.on('pageerror', (err) => errors.push(`PAGE ERROR: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`BROWSER ERROR: ${msg.text()}`);
  });

  await page.goto('/');
  await tryLogin(page);

  const rng = mulberry32(SEED);
  const actions = buildChaosActions(page, rng);
  const iterations = 80;

  for (let i = 0; i < iterations; i++) {
    const idx = Math.floor(rng() * actions.length);
    actionLog.push(`#${i + 1} action[${idx}]`);
    try {
      await actions[idx]();
      await page.waitForTimeout(150);
    } catch {
      // Swallow — we only care that the app survives
    }
  }

  expect(errors, `Errors after chaos run (seed=${SEED}):\n${actionLog.join('\n')}`).toEqual([]);

  // App should still be responsive
  await page.goto('/');
  await expect(page.locator('body')).toBeVisible();
});
