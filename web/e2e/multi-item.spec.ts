import { expect, test } from "@playwright/test";

test("multi-item return: switching items shows each item's own routing, no leftover state", async ({
  page,
}) => {
  await page.goto("/returns/new");

  await page.getByRole("button", { name: /multi item return/i }).click();
  await expect(page.getByText(/RET-2026-\d{3}/)).toBeVisible();

  await page.getByRole("button", { name: /run reconciliation/i }).click();

  await expect(page.getByRole("heading", { name: "RET-2026-008" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText("Requires review").first()).toBeVisible();

  // Item A (default): clean RESTOCK
  await expect(page.getByText("20").first()).toBeVisible();
  await expect(page.getByText("Restock").first()).toBeVisible();

  // Item B: unsafe damage overrides supplier RESTOCK preference, routes SCRAP
  await page.getByRole("button", { name: "YOGURT-22-1" }).click();
  await expect(page.getByText("8").first()).toBeVisible();
  await expect(page.getByText("Scrap").first()).toBeVisible();

  // Item C: unresolved batch identity, routes QUARANTINE despite supplier RESTOCK
  await page.getByRole("button", { name: "SAUCE-99-1" }).click();
  await expect(page.getByText("12").first()).toBeVisible();
  await expect(page.getByText("Quarantine").first()).toBeVisible();

  // Switching back to Item A must not show Item C's leftover routing
  await page.getByRole("button", { name: "CEREAL-12-1" }).click();
  await expect(page.getByText("Restock").first()).toBeVisible();
});
