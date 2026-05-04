import { test, expect } from '@playwright/test';

test('aggressive stress flow', async ({ page }) => {
  await page.goto('http://localhost:8080/search');

  // --- Login helper ---
  async function login(user: string) {
    await page.getByRole('button', { name: 'Sign in with Microsoft Entra' }).click();
    await page.getByRole('textbox', { name: 'Username or email' }).fill(user);
    await page.getByRole('textbox', { name: 'Password' }).fill('pass');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page.getByRole('textbox', { name: /Search for documents/i }))
      .toBeVisible();
  }

  await page.getByRole('button', { name: 'Go to login' }).click();
  await login('muaw22');

  const searchInput = page.getByRole('textbox', { name: /Search for documents/i });
  const editBtn = page.getByRole('button', { name: 'Edit' });

  // --- Aggressive search loop ---
  for (let i = 0; i < 3; i++) {
    await searchInput.fill(`test ${i}`);
    await page.getByRole('button', { name: /^Search$/ }).click();

    const file = page.getByRole('button', { name: /CMakeLists.txt/i });
    await expect(file).toBeVisible();
    await file.click();

    await expect(editBtn).toBeVisible();

    // --- Aggressive edit spam (controlled) ---
    for (let j = 0; j < 5; j++) {
      await editBtn.click();
      await expect(editBtn).toBeVisible(); // ensures UI didn’t break
    }

    // Validate metadata each loop
    await expect(page.getByText(/Security Class/i)).toBeVisible();
    await expect(page.getByText(/File Size/i)).toBeVisible();

    await page.getByRole('button', { name: 'Close preview' }).click();
  }

  // --- Aggressive AI actions ---
  const secondFile = page.getByRole('button', { name: /golden_commands.txt/i });
  await secondFile.click();

  await expect(editBtn).toBeVisible();

  const aiButtons = [
    'Generate AI Summary',
    'Find Similar Files',
    'Regenerate Similar Files'
  ];

  for (const name of aiButtons) {
    const btn = page.getByRole('button', { name });
    await expect(btn).toBeVisible();
    await btn.click();
  }

  // --- Aggressive similar selection ---
  const similarItems = page.getByRole('listitem');
  const count = await similarItems.count();

  for (let i = 0; i < Math.min(count, 5); i++) {
    await similarItems.nth(i).click();
  }

  await page.getByRole('button', { name: 'Merge Files' }).click();
  await page.getByRole('button', { name: 'Merge & Summarize' }).click();

  await page.keyboard.press('Escape');

  // --- Settings stress toggling ---
  await page.getByRole('button', { name: 'Security & Compliance' }).click();
  await page.getByRole('button', { name: 'System Settings' }).click();

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
    'Confidential'
  ];

  for (let round = 0; round < 2; round++) {
    for (const name of toggles) {
      const btn = page.getByRole('button', { name, exact: true });
      if (await btn.isVisible()) {
        await btn.click();
      }
    }
  }

  await page.getByRole('button', { name: 'Clear all' }).click();

  // --- Notification spam (bounded) ---
  const notifications = page.getByRole('button', { name: 'Notifications' });
  for (let i = 0; i < 3; i++) {
    await notifications.click();
    await expect(notifications).toBeVisible();
  }

  // --- Logout / Login switch ---
  await page.getByRole('button', { name: 'Logout' }).click();
  await login('osoh22');

  // --- Final aggressive validation ---
  for (let i = 0; i < 2; i++) {
    await searchInput.fill('test');
    await page.getByRole('button', { name: /^Search$/ }).click();

    const file = page.getByRole('button', { name: /CMakeLists.txt/i });
    await expect(file).toBeVisible();
    await file.click();

    await expect(page.getByText(/Security Class/i)).toBeVisible();

    await page.getByRole('button', { name: 'Close preview' }).click();
  }

  await page.getByRole('button', { name: 'Logout' }).click();
});