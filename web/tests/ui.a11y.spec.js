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
  const topbar = page.locator("header.ptTopbar");
  const skipLink = page.getByRole("link", { name: "Skip to workspace" }).first();
  const guidedButton = topbar.getByRole("button", { name: "Guided", exact: true });
  const powerButton = topbar.getByRole("button", { name: "Power", exact: true });
  const compileButton = topbar.getByRole("button", { name: "Compile", exact: true });

  await page.locator("body").press("Tab");
  await expect(skipLink).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(guidedButton).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(powerButton).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(compileButton).toBeFocused();
});

test("keyboard reverse tab returns to previous control", async ({ page }) => {
  const topbar = page.locator("header.ptTopbar");
  const guidedButton = topbar.getByRole("button", { name: "Guided", exact: true });
  const powerButton = topbar.getByRole("button", { name: "Power", exact: true });
  const compileButton = topbar.getByRole("button", { name: "Compile", exact: true });

  await page.locator("body").press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(compileButton).toBeFocused();

  await page.keyboard.press("Shift+Tab");
  await expect(powerButton).toBeFocused();

  await page.keyboard.press("Shift+Tab");
  await expect(guidedButton).toBeFocused();
});

test("skip link moves focus to main workspace", async ({ page }) => {
  const skipLink = page.getByRole("link", { name: "Skip to workspace" }).first();
  const workspaceMain = page.locator("#pt-main-workspace");

  await page.locator("body").press("Tab");
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
    await secondTab.focus();
    await page.keyboard.press("Enter");
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
