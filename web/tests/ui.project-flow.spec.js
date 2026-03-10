import { expect, test } from "@playwright/test";

import { buildRun, buildRunManifest, installMockApi } from "./helpers/mockProjectApi";

test("landing bootstraps the sample project workspace", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  const mock = await installMockApi(page);

  await page.goto("/");

  await expect(page.locator('section[aria-label="Product landing workspace"]')).toBeVisible();
  await expect
    .poll(() => mock.requests.bootstrapCalls.length)
    .toBe(1);

  const projectSelect = page
    .locator('section[aria-label="Workspace context bar"]')
    .locator("label")
    .filter({ hasText: "Project" })
    .first()
    .locator("select");

  await expect.poll(async () => projectSelect.inputValue()).toBe("pilot_demo");

  await page.getByRole("button", { name: "Continue to workspace", exact: true }).click();
  await expect(page.locator('section[aria-label="Product landing workspace"]')).toBeHidden();
});

test("project workspace autosaves and restores after reload", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("pt_show_landing", "0");
    localStorage.setItem("pt_project_id", "pilot_demo");
  });
  const mock = await installMockApi(page, {
    workspace: {
      stage: "certify",
      mode: "runs",
      active_right_tab: "manifest",
      user_mode: "exec",
      selected_run_id: "abcdef12345678",
    },
  });

  await page.goto("/");

  const activeStage = page.locator('nav[aria-label="Product stage navigation"] button.ptStagePill.active');
  const rolePreset = page
    .locator('section[aria-label="Workspace context bar"]')
    .locator("label")
    .filter({ hasText: "Role preset" })
    .first()
    .locator("select");
  const modeSelect = page.locator("header.ptTopbar label").filter({ hasText: "Mode" }).first().locator("select");

  await expect(activeStage).toHaveText("Certify");
  await expect(rolePreset).toHaveValue("exec");
  await expect(modeSelect).toHaveValue("runs");

  await page.getByRole("navigation", { name: "Product stage navigation" }).getByRole("button", { name: "Build" }).click();
  await expect(activeStage).toHaveText("Build");
  await expect
    .poll(() => mock.requests.workspacePuts.at(-1)?.stage || "")
    .toBe("build");

  await page.reload();

  await expect(activeStage).toHaveText("Build");
  await expect(page.locator("header.ptTopbar label").filter({ hasText: "Mode" }).first().locator("select")).toHaveValue("graph");
});

test("certification workspace publishes and verifies a packet", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("pt_show_landing", "0");
    localStorage.setItem("pt_project_id", "pilot_demo");
  });
  const mock = await installMockApi(page, {
    workspace: {
      stage: "certify",
      mode: "runs",
      active_right_tab: "manifest",
      user_mode: "reviewer",
      selected_run_id: "abcdef12345678",
    },
  });

  await page.goto("/");

  const certWorkspace = page.locator('section[aria-label="Certification workspace"]');
  await expect(certWorkspace).toBeVisible();

  await certWorkspace.getByRole("button", { name: "Publish shareable packet", exact: true }).click();
  await expect
    .poll(() => mock.requests.publishCalls.length)
    .toBe(1);
  await expect(certWorkspace.getByText("digest=deadbeefcafebabe1234", { exact: true })).toBeVisible();

  await certWorkspace.getByRole("button", { name: "Verify published packet", exact: true }).click();
  await expect
    .poll(() => mock.requests.verifyCalls.length)
    .toBe(1);
  await expect(certWorkspace.getByText("verify=ok, files=4, missing=0, mismatched=0", { exact: true })).toBeVisible();

  const publishedLink = certWorkspace.getByRole("link", { name: "Open published link", exact: true });
  await expect(publishedLink).toHaveAttribute("href", "http://127.0.0.1:8000/v0/evidence/bundle/by-digest/deadbeefcafebabe1234");
});

test("compare selections and approvals survive a reload", async ({ page }) => {
  const baselineRunId = "baseline12345678";
  const candidateRunId = "candidate87654321";

  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("pt_show_landing", "0");
    localStorage.setItem("pt_project_id", "pilot_demo");
  });

  const mock = await installMockApi(page, {
    runs: [
      buildRun("pilot_demo", baselineRunId, "2026-03-07T11:00:00Z"),
      buildRun("pilot_demo", candidateRunId, "2026-03-07T12:00:00Z"),
    ],
    runManifests: {
      [baselineRunId]: {
        ...buildRunManifest("pilot_demo", baselineRunId),
        input: { project_id: "pilot_demo", protocol_selected: "BB84" },
      },
      [candidateRunId]: {
        ...buildRunManifest("pilot_demo", candidateRunId),
        input: { project_id: "pilot_demo", protocol_selected: "BBM92" },
      },
    },
    workspace: {
      stage: "compare",
      mode: "runs",
      active_right_tab: "diff",
      user_mode: "reviewer",
      selected_run_id: candidateRunId,
      compare: {
        baseline_run_id: null,
        candidate_run_ids: [],
        scope: "input",
      },
    },
  });

  await page.goto("/");

  const activeStage = page.locator('nav[aria-label="Product stage navigation"] button.ptStagePill.active');
  const diffTab = page.getByRole("tab", { name: "Diff", exact: true });
  const manifestTab = page.getByRole("tab", { name: "Manifest", exact: true });
  const compareLab = page.locator('section[aria-label="Week 6 compare lab panel"]');
  const baselineSelect = compareLab.getByRole("combobox", { name: "Baseline run", exact: true });
  const candidateSelect = compareLab.getByRole("combobox", { name: "Candidate run", exact: true });
  const scopeSelect = compareLab.getByRole("combobox", { name: "Scope", exact: true });

  await expect(activeStage).toHaveText("Compare");
  await expect(compareLab).toBeVisible();

  await baselineSelect.selectOption(baselineRunId);
  await candidateSelect.selectOption(candidateRunId);
  await scopeSelect.selectOption("all");
  await compareLab.getByRole("button", { name: "Compare baseline vs candidate", exact: true }).click();

  await expect
    .poll(() => mock.requests.diffCalls.length)
    .toBe(1);
  await expect(compareLab.getByText("new: 1 | resolved: 0 | applicability-changed: 0", { exact: true })).toBeVisible();
  await expect(compareLab.getByText("input.protocol_selected: BB84 -> BBM92", { exact: true })).toBeVisible();
  await expect
    .poll(() =>
      mock.requests.workspacePuts.some(
        (workspace) =>
          workspace?.compare?.baseline_run_id === baselineRunId &&
          workspace?.compare?.candidate_run_ids?.[0] === candidateRunId &&
          workspace?.compare?.scope === "all",
      ),
    )
    .toBe(true);

  await manifestTab.click();
  const certWorkspace = page.locator('section[aria-label="Certification workspace"]');
  await expect(certWorkspace).toBeVisible();
  await certWorkspace.getByLabel("actor", { exact: true }).fill("reviewer@test");
  await certWorkspace.getByLabel("note", { exact: true }).fill("Reviewed diff and approved candidate.");
  await certWorkspace.getByRole("button", { name: "Approve Selected Run", exact: true }).click();

  await expect
    .poll(() => mock.requests.approvalPosts.length)
    .toBe(1);
  await expect
    .poll(() => mock.requests.workspacePuts.some((workspace) => workspace?.active_right_tab === "manifest"))
    .toBe(true);
  const approvalJson = page.locator("pre").filter({ hasText: '"actor": "reviewer@test"' }).first();
  await expect(approvalJson).toBeVisible();

  await page.reload();

  await expect(activeStage).toHaveText("Compare");
  await expect(manifestTab).toHaveAttribute("aria-selected", "true");
  await expect(approvalJson).toBeVisible();

  await diffTab.click();
  await expect(compareLab).toBeVisible();
  await expect(baselineSelect).toHaveValue(baselineRunId);
  await expect(candidateSelect).toHaveValue(candidateRunId);
  await expect(scopeSelect).toHaveValue("all");
});
