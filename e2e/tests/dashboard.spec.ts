import { expect, test } from "@playwright/test";

test("reviewer runs an analysis and sees the AI reliability panel", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Claims Queue" })).toBeVisible();

  await page.locator('a[href^="/claims/"]').first().click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  const run = page.getByRole("button", { name: /Run AI Analysis|Re-run AI Analysis/ });
  await run.click();
  await expect(page.getByText("Agent Reasoning & Recommendation")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByText("AI Reliability")).toBeVisible();
  await expect(page.getByText("Rule engine (AI unavailable)")).toBeVisible(); // offline mode

  // Reviewer feedback round trip.
  await page.getByLabel("Reviewer name").fill("e2e-reviewer");
  await page.getByRole("button", { name: "Agree with AI" }).click();
  await expect(page.getByText("Thanks, your review was recorded.")).toBeVisible();
});
