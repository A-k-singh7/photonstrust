import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.goto("/");
});

test("loads main shell", async ({ page }) => {
  await expect(page.locator("header.ptTopbar .ptBrandTitle")).toHaveText("PhotonTrust");
  await expect(page.locator("header.ptTopbar")).toBeVisible();
});

test("shows product stage navigation", async ({ page }) => {
  const stageNav = page.getByRole("navigation", { name: "Product stage navigation" });
  await expect(stageNav).toBeVisible();
  await expect(stageNav.getByRole("button", { name: "Build" })).toBeVisible();
  await expect(stageNav.getByRole("button", { name: "Run" })).toBeVisible();
  await expect(stageNav.getByRole("button", { name: "Validate" })).toBeVisible();
});

test("shows topbar run button", async ({ page }) => {
  const runButton = page.locator("header.ptTopbar").getByRole("button", {
    name: "Run",
    exact: true,
  });
  await expect(runButton).toBeVisible();
  await expect(runButton).toBeEnabled();
});
