import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("pt_show_landing", "0");
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

test("guided mode shows guidance checklist and compare checklist action opens compare flows", async ({ page }) => {
  const guidanceStrip = page.locator('section[aria-label="Start here guidance"]');
  const checklist = guidanceStrip.getByRole("list", { name: "Onboarding checklist" });
  const compareStep = checklist.getByRole("listitem").filter({ hasText: "Compare baseline vs candidate" });
  const compareStepOpen = compareStep.getByRole("button", { name: "Open", exact: true });
  const modeSelect = page.locator("header.ptTopbar label").filter({ hasText: "Mode" }).first().locator("select");
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
  await expect.poll(async () => modeSelect.inputValue()).toBe("runs");
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
  const experienceSelect = page.locator("header.ptTopbar label").filter({ hasText: "Experience" }).first().locator("select");
  const profileSelect = page.locator("header.ptTopbar label").filter({ hasText: "Profile" }).first().locator("select");
  const guidanceStrip = page.locator('section[aria-label="Start here guidance"]');
  const switchToPowerButton = guidanceStrip.getByRole("button", { name: "Switch to Power", exact: true });
  const drcTab = page.getByRole("tab", { name: "DRC", exact: true });

  await expect.poll(async () => experienceSelect.inputValue()).toBe("guided");
  await profileSelect.selectOption("pic_circuit");
  await expect(drcTab).toHaveCount(0);

  await switchToPowerButton.click();

  await expect.poll(async () => experienceSelect.inputValue()).toBe("power");
  await expect(drcTab).toBeVisible();
});
