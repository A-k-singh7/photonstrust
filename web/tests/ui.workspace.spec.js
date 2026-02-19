import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.goto("/");
});

test("shows workspace context bar with project role and view controls", async ({ page }) => {
  const contextBar = page.locator('section[aria-label="Workspace context bar"]');
  const projectSelect = contextBar.locator("label").filter({ hasText: "Project" }).first().locator("select");
  const rolePresetSelect = contextBar.locator("label").filter({ hasText: "Role preset" }).first().locator("select");
  const savedViewSelect = contextBar.locator("label").filter({ hasText: "Saved view" }).first().locator("select");

  await expect(contextBar).toBeVisible();
  await expect(projectSelect).toBeVisible();
  await expect(rolePresetSelect).toBeVisible();
  await expect(savedViewSelect).toBeVisible();
});

test("Save View adds a recent activity chip", async ({ page }) => {
  const topbarSaveView = page.locator("header.ptTopbar").getByRole("button", { name: "Save View", exact: true });
  const contextBar = page.locator('section[aria-label="Workspace context bar"]');
  const activityChip = contextBar.getByRole("button", { name: "Saved workspace view preset.", exact: true });

  await expect(topbarSaveView).toBeVisible();
  await topbarSaveView.click();
  await expect(activityChip).toBeVisible();
});

test("selecting Reviewer role highlights Compare stage or shows runs cues", async ({ page }) => {
  const contextBar = page.locator('section[aria-label="Workspace context bar"]');
  const rolePreset = contextBar.locator("label").filter({ hasText: "Role preset" }).first().locator("select");
  const compareActive = page.locator('nav[aria-label="Product stage navigation"] button.ptStagePill.active').filter({
    hasText: "Compare",
  });
  const modeSelect = page.getByLabel("Mode", { exact: true });
  const runsBrowser = page.locator('section[aria-label="Run registry browser"]');

  await rolePreset.selectOption("reviewer");

  await expect
    .poll(async () => {
      if ((await compareActive.count()) > 0 && (await compareActive.first().isVisible())) {
        return "compare";
      }

      const modeValue = await modeSelect.inputValue();
      if (modeValue === "runs" && (await runsBrowser.isVisible().catch(() => false))) {
        return "runs";
      }

      return "pending";
    })
    .toMatch(/^(compare|runs)$/);
});
