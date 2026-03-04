import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("pt_show_landing", "0");
  });
  await page.goto("/");
});

test("keyboard tab order starts with skip link and top controls", async ({ page }) => {
  const skipLink = page.getByRole("link", { name: "Skip to workspace" }).first();
  const modeSelect = page.locator("header.ptTopbar label").filter({ hasText: "Mode" }).first().locator("select");
  const experienceSelect = page.locator("header.ptTopbar label").filter({ hasText: "Experience" }).first().locator("select");
  const userModeSelect = page.locator("header.ptTopbar label").filter({ hasText: "User mode" }).first().locator("select");
  const viewPresetSelect = page.locator("header.ptTopbar label").filter({ hasText: "View preset" }).first().locator("select");
  const saveViewButton = page.locator("header.ptTopbar button", { hasText: "Save View" }).first();

  await page.keyboard.press("Tab");
  await expect(skipLink).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(modeSelect).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(experienceSelect).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(userModeSelect).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(viewPresetSelect).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(saveViewButton).toBeFocused();
});

test("keyboard reverse tab returns to previous control", async ({ page }) => {
  const experienceSelect = page.locator("header.ptTopbar label").filter({ hasText: "Experience" }).first().locator("select");
  const userModeSelect = page.locator("header.ptTopbar label").filter({ hasText: "User mode" }).first().locator("select");
  const viewPresetSelect = page.locator("header.ptTopbar label").filter({ hasText: "View preset" }).first().locator("select");
  const saveViewButton = page.locator("header.ptTopbar button", { hasText: "Save View" }).first();

  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(saveViewButton).toBeFocused();

  await page.keyboard.press("Shift+Tab");
  await expect(viewPresetSelect).toBeFocused();

  await page.keyboard.press("Shift+Tab");
  await expect(userModeSelect).toBeFocused();

  await page.keyboard.press("Shift+Tab");
  await expect(experienceSelect).toBeFocused();
});

test("skip link moves focus to main workspace", async ({ page }) => {
  const skipLink = page.getByRole("link", { name: "Skip to workspace" }).first();
  const workspaceMain = page.locator("#pt-main-workspace");

  await page.keyboard.press("Tab");
  await expect(skipLink).toBeFocused();

  await page.keyboard.press("Enter");
  await expect(workspaceMain).toBeFocused();
});

test("right sidebar tabs expose tab semantics", async ({ page }) => {
  const rightSidebar = page.locator("aside.ptSidebarRight").first();
  const tablist = rightSidebar.getByRole("tablist").first();

  await expect(tablist).toBeVisible();

  const tabs = tablist.getByRole("tab");
  await expect(tabs.first()).toBeVisible();
  await expect
    .poll(async () => await tabs.count())
    .toBeGreaterThan(0);

  const firstTab = tabs.first();
  await expect(firstTab).toHaveAttribute("aria-selected", /^(true|false)$/);

  if ((await tabs.count()) > 1) {
    const secondTab = tabs.nth(1);
    await secondTab.click();
    await expect(secondTab).toHaveAttribute("aria-selected", "true");
    await expect(firstTab).toHaveAttribute("aria-selected", "false");

    await secondTab.focus();
    await page.keyboard.press("Home");
    await expect(firstTab).toBeFocused();
    await expect(firstTab).toHaveAttribute("aria-selected", "true");

    await page.keyboard.press("ArrowRight");
    await expect(secondTab).toBeFocused();
    await expect(secondTab).toHaveAttribute("aria-selected", "true");
  }
});
