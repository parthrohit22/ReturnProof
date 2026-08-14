import { expect, test } from "@playwright/test";

const SCENARIOS = [
  "simple condition conflict",
  "batch corruption",
  "out of order supplier",
  "quantity dispute",
  "partial allocation",
];

for (const scenario of SCENARIOS) {
  test(`${scenario}: loads and runs without console errors`, async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => consoleErrors.push(err.message));

    await page.goto("/returns/new");
    await page.getByRole("button", { name: new RegExp(scenario, "i") }).click();
    await page.getByRole("button", { name: /run reconciliation/i }).click();

    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/resolved|requires review/i).first()).toBeVisible();

    expect(consoleErrors).toEqual([]);
  });
}

test("a saved reconciliation survives a page refresh", async ({ page }) => {
  await page.goto("/returns/new");
  await page.getByRole("button", { name: /compound failure/i }).click();
  await page.getByRole("button", { name: /run reconciliation/i }).click();

  await expect(page.getByRole("heading", { name: "RET-2026-001" })).toBeVisible({
    timeout: 15_000,
  });
  const url = page.url();

  await page.reload();

  await expect(page.getByRole("heading", { name: "RET-2026-001" })).toBeVisible();
  expect(page.url()).toBe(url);
});

test("returns queue lists a persisted run and links back into it", async ({ page }) => {
  await page.goto("/returns/new");
  await page.getByRole("button", { name: /compound unresolved/i }).click();
  await page.getByRole("button", { name: /run reconciliation/i }).click();
  await expect(page.getByText("Requires review").first()).toBeVisible({ timeout: 15_000 });

  await page.goto("/returns");
  const row = page.getByRole("link", { name: "RET-2026-007" }).first();
  await expect(row).toBeVisible();
  await row.click();
  await expect(page.getByRole("heading", { name: "RET-2026-007" })).toBeVisible();
});
