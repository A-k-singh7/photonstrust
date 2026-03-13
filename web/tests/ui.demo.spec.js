import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("pt_show_landing", "0");
  });
  await page.goto("/");
});

test("demo mode locks narrative scenes and stage progression", async ({ page }) => {
  const topbar = page.locator("header.ptTopbar");
  const advancedToggle = topbar.locator("summary", { hasText: "Advanced setup and diagnostics" }).first();
  const demoModeButton = topbar.getByRole("button", { name: "Demo Mode", exact: true });
  const orchestrator = page.locator('section[aria-label="Demo mode narrative orchestrator"]');
  const stageNav = page.getByRole("navigation", { name: "Product stage navigation" });
  const activeStagePill = stageNav.locator("button.ptStagePill.active");
  const nextButton = orchestrator.getByRole("button", { name: "Next", exact: true });

  await advancedToggle.click();
  await demoModeButton.click();

  await expect(orchestrator).toBeVisible();
  await expect(activeStagePill).toHaveText("Compare");

  await nextButton.click();
  await expect(activeStagePill).toHaveText("Certify");

  await nextButton.click();
  await expect(activeStagePill).toHaveText("Run");

  await nextButton.click();
  await expect(activeStagePill).toHaveText("Export");
});

test("demo mode exits and unlocks controls", async ({ page }) => {
  const topbar = page.locator("header.ptTopbar");
  const advancedToggle = topbar.locator("summary", { hasText: "Advanced setup and diagnostics" }).first();
  const demoModeButton = topbar.getByRole("button", { name: "Demo Mode", exact: true });
  const orchestrator = page.locator('section[aria-label="Demo mode narrative orchestrator"]');
  const compileButton = topbar.getByRole("button", { name: "Compile", exact: true });
  const runButton = topbar.getByRole("button", { name: "Run", exact: true });
  const diffButton = topbar.getByRole("button", { name: "Diff", exact: true });

  async function visibleActionButton() {
    if (await compileButton.isVisible().catch(() => false)) return compileButton;
    if (await runButton.isVisible().catch(() => false)) return runButton;
    if (await diffButton.isVisible().catch(() => false)) return diffButton;
    return null;
  }

  await advancedToggle.click();
  await demoModeButton.click();
  await expect(orchestrator).toBeVisible();

  const actionDuringDemo = await visibleActionButton();
  expect(actionDuringDemo).not.toBeNull();
  await expect(actionDuringDemo).toBeDisabled();

  await orchestrator.getByRole("button", { name: "Exit demo", exact: true }).click();

  await expect(orchestrator).toBeHidden();

  const actionAfterExit = await visibleActionButton();
  expect(actionAfterExit).not.toBeNull();
  await expect(actionAfterExit).toBeEnabled();
});
