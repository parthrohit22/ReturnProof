import { expect, test } from "@playwright/test";

test("resolvable compound failure: full evidence, 6 scrap, 18 restock", async ({ page }) => {
  await page.goto("/returns/new");

  await page.getByRole("button", { name: /compound failure/i }).click();
  await expect(page.getByText(/RET-2026-\d{3}/)).toBeVisible();

  await page.getByRole("button", { name: /run reconciliation/i }).click();

  await expect(page.getByRole("heading", { name: "RET-2026-001" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText("Resolved", { exact: true })).toBeVisible();

  await expect(page.getByText("6").first()).toBeVisible();
  await expect(page.getByText("Scrap").first()).toBeVisible();
  await expect(page.getByText("18").first()).toBeVisible();
  await expect(page.getByText("Restock").first()).toBeVisible();
  await expect(page.getByText("2026-10")).toBeVisible();
  await expect(page.getByText("PASS")).toBeVisible();

  await page.getByRole("button", { name: "Decision" }).click();
  await expect(page.getByText("BA1902").first()).toBeVisible();
});

test("unresolved compound failure: insufficient evidence quarantines instead of guessing", async ({
  page,
}) => {
  await page.goto("/returns/new");

  await page.getByRole("button", { name: /compound unresolved/i }).click();
  await expect(page.getByText(/RET-2026-\d{3}/)).toBeVisible();

  await page.getByRole("button", { name: /run reconciliation/i }).click();

  await expect(page.getByText("Requires review").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Quarantine").first()).toBeVisible();
});
