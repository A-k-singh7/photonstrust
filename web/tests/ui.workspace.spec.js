import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("pt_show_landing", "0");
  });
  await page.goto("/");
});

async function openContextControls(page) {
  const contextBar = page.locator('section[aria-label="Workspace context bar"]');
  const controls = contextBar.locator("details.ptWorkspaceControls");
  const summary = controls.locator("summary");

  await expect(contextBar).toBeVisible();
  await expect(summary).toBeVisible();
  await summary.click();
  await expect(controls).toHaveAttribute("open", "");

  return { contextBar, controls };
}

test("shows workspace context bar with project role and view controls", async ({ page }) => {
  const { controls } = await openContextControls(page);
  const projectSelect = controls.locator("label").filter({ hasText: "Project" }).first().locator("select");
  const rolePresetSelect = controls.locator("label").filter({ hasText: "Role preset" }).first().locator("select");
  const savedViewSelect = controls.locator("label").filter({ hasText: "Saved view" }).first().locator("select");

  await expect(projectSelect).toBeVisible();
  await expect(rolePresetSelect).toBeVisible();
  await expect(savedViewSelect).toBeVisible();
});

test("Save View adds a recent activity chip", async ({ page }) => {
  const { contextBar, controls } = await openContextControls(page);
  const contextSaveView = controls.getByRole("button", { name: "Save view", exact: true });
  const activityChip = contextBar.getByRole("button", { name: "Saved workspace view preset.", exact: true });

  await expect(contextSaveView).toBeVisible();
  await contextSaveView.click();
  await expect(activityChip).toBeVisible();
});

test("selecting Reviewer role highlights Compare stage or shows runs cues", async ({ page }) => {
  const { controls } = await openContextControls(page);
  const rolePreset = controls.locator("label").filter({ hasText: "Role preset" }).first().locator("select");
  const compareActive = page.locator('nav[aria-label="Product stage navigation"] button.ptStagePill.active').filter({
    hasText: "Compare",
  });
  const runsBrowser = page.locator('section[aria-label="Run registry browser"]');
  const compareLab = page.locator('section[aria-label="Week 6 compare lab panel"]');

  await rolePreset.selectOption("reviewer");

  await expect
    .poll(async () => {
      if ((await compareActive.count()) > 0 && (await compareActive.first().isVisible())) {
        return "compare";
      }

      if ((await runsBrowser.isVisible().catch(() => false)) || (await compareLab.isVisible().catch(() => false))) {
        return "runs";
      }

      return "pending";
    })
    .toMatch(/^(compare|runs)$/);
});

test("guided mode shows guidance checklist and compare checklist action opens compare flows", async ({ page }) => {
  const guidanceStrip = page.locator('section[aria-label="Start here guidance"]');
  const checklist = guidanceStrip.getByRole("list", { name: "Onboarding checklist" });
  const compareStep = checklist.getByRole("listitem").filter({ hasText: "Compare baseline vs candidate" });
  const compareStepOpen = compareStep.getByRole("button", { name: "Open", exact: true });
  const compareStage = page.locator('nav[aria-label="Product stage navigation"] button.ptStagePill.active').filter({
    hasText: "Compare",
  });
  const compareLab = page.locator('section[aria-label="Week 6 compare lab panel"]');
  const baselineSelect = page.getByLabel("Baseline run", { exact: true });
  const candidateSelect = page.getByLabel("Candidate run", { exact: true });

  await expect(guidanceStrip).toBeVisible();
  await expect(checklist).toBeVisible();
  await expect(checklist.getByText("Check API health", { exact: true })).toBeVisible();
  await expect(checklist.getByText("Run first simulation", { exact: true })).toBeVisible();
  await expect(checklist.getByText("Compare baseline vs candidate", { exact: true })).toBeVisible();
  await expect(checklist.getByText("Review decision and blockers", { exact: true })).toBeVisible();

  await compareStepOpen.click();

  await expect(compareStage).toBeVisible();
  await expect(compareLab).toBeVisible();

  await expect
    .poll(async () => {
      const baselineOptionCount = await baselineSelect.locator("option").count();
      const candidateOptionCount = await candidateSelect.locator("option").count();
      if (baselineOptionCount <= 1 && candidateOptionCount <= 1) {
        return "none";
      }
      const baselineValue = (await baselineSelect.inputValue()).trim();
      const candidateValue = (await candidateSelect.inputValue()).trim();
      return baselineValue || candidateValue ? "prefilled" : "options_without_prefill";
    })
    .toMatch(/^(none|prefilled)$/);
});

test("switching to Power experience updates selector and enables PIC advanced tabs", async ({ page }) => {
  const topbar = page.locator("header.ptTopbar");
  const guidedButton = topbar.getByRole("button", { name: "Guided", exact: true });
  const powerButton = topbar.getByRole("button", { name: "Power", exact: true });
  const topbarDetails = topbar.locator("details.ptTopbarDetails");
  const profileSelect = topbarDetails.locator("label").filter({ hasText: "Profile" }).first().locator("select");
  const guidanceStrip = page.locator('section[aria-label="Start here guidance"]');
  const switchToPowerButton = guidanceStrip.getByRole("button", { name: "Switch to Power", exact: true });
  const drcTab = page.getByRole("tab", { name: "DRC", exact: true });

  await expect(guidedButton).toHaveClass(/active/);
  await topbarDetails.locator("summary").click();
  await profileSelect.selectOption("pic_circuit");
  await expect(drcTab).toHaveCount(0);

  await switchToPowerButton.click();

  await expect(powerButton).toHaveClass(/active/);
  await expect(drcTab).toBeVisible();
});
