import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { chromium } from "playwright-core";
import { createServer } from "vite";
import { MENU_ITEMS } from "../src/config/menuDefinitions.js";

const browserPath = process.env.FRONTEND_SMOKE_BROWSER_PATH || (
  process.platform === "win32"
    ? path.join(process.env.PROGRAMFILES || "C:\\Program Files", "Google/Chrome/Application/chrome.exe")
    : ["/usr/bin/chromium", "/usr/bin/google-chrome"].find(existsSync)
);

async function colors(locator) {
  return locator.evaluate((element) => {
    const style = getComputedStyle(element);
    return { background: style.backgroundColor, color: style.color, border: style.borderColor, position: style.backgroundPosition };
  });
}

test("login, order actions, recall tabs and mobile controls use the shared palette", { skip: !browserPath || !existsSync(browserPath) }, async () => {
  const vite = await createServer({ server: { host: "127.0.0.1", port: 0, hmr: false } });
  await vite.listen();
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  const base = `http://127.0.0.1:${vite.httpServer.address().port}`;
  const black = "rgb(17, 17, 17)";
  const white = "rgb(255, 255, 255)";

  try {
    await page.goto(base);
    const login = page.locator(".login-submit");
    await login.waitFor();
    assert.deepEqual((({ background, color, border }) => ({ background, color, border }))(await colors(login)),
      { background: white, color: black, border: black });
    await login.hover();
    await page.waitForTimeout(450);
    assert.equal((await colors(login)).color, white);

    await context.addInitScript(() => localStorage.setItem("assetManager.accessToken", "test-token"));
    let mockUser = { id: 1, username: "admin", name: "관리자", role: "admin", menu_permissions: [], is_active: true };
    await page.route("http://127.0.0.1:8010/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      const body = pathname === "/auth/me"
        ? mockUser
        : pathname === "/menu-visibility"
          ? { visibility: Object.fromEntries(MENU_ITEMS.map((item) => [item.menuKey, true])) }
          : pathname.endsWith("/channels")
            ? [{ id: 1, name: "스마트스토어", code: "smartstore", is_active: true, is_default: true, processing_supported: false }]
            : { items: [], total: 0 };
      await route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "*" }, body: JSON.stringify(body) });
    });

    await page.goto(`${base}/online`);
    const onlineHome = page.locator('.portal-sidebar .sidebar-menu-item[aria-current="page"]');
    await onlineHome.waitFor();
    assert.match(await onlineHome.innerText(), /온라인 TEAM 홈/);
    assert.equal((await colors(onlineHome)).background, black);
    assert.equal((await colors(onlineHome)).color, white);
    assert.equal(await onlineHome.evaluate((element) => getComputedStyle(element).borderTopWidth), "0px");
    assert.equal(await onlineHome.locator("span").evaluate((element) => getComputedStyle(element).color), white);
    for (const title of ["업무", "자산", "인사팀", "온라인 TEAM", "관리"]) {
      const groupTitle = page.locator(".portal-nav-group-title", { hasText: title });
      assert.equal(await groupTitle.evaluate((element) => getComputedStyle(element).borderBottomWidth), "1px");
    }
    const plainMenu = page.locator(".portal-sidebar .sidebar-menu-item").filter({ hasText: "리콜 관리" });
    assert.equal((await colors(plainMenu)).color, black);
    assert.equal(await plainMenu.evaluate((element) => getComputedStyle(element).borderTopWidth), "0px");
    await plainMenu.hover();
    await page.waitForTimeout(450);
    assert.equal((await colors(plainMenu)).background, "rgb(243, 244, 246)");
    assert.equal((await colors(plainMenu)).color, black);
    const editMenu = page.locator(".sidebar-edit-heading .sidebar-edit-button");
    assert.equal((await colors(editMenu)).background, white);
    assert.equal((await colors(editMenu)).color, black);
    await editMenu.hover();
    await page.waitForTimeout(450);
    assert.equal((await colors(editMenu)).background, black);
    assert.equal((await colors(editMenu)).color, white);
    await editMenu.click();
    await page.getByRole("button", { name: "취소", exact: true }).click();
    await plainMenu.click();
    await page.waitForURL("**/online/recall");
    await page.goBack();
    await page.waitForURL("**/online");

    await page.goto(`${base}/online/orders/settings`);
    const add = page.locator(".online-order-channel-heading button");
    await add.waitFor();
    assert.equal((await colors(add)).background, white);
    await add.click();
    assert.equal(await page.locator(".online-order-channel-checks").evaluate((element) => getComputedStyle(element).display), "flex");
    assert.deepEqual(await page.locator(".online-order-channel-checks label").evaluateAll((elements) => elements.map((element) => getComputedStyle(element).display)), ["flex", "flex"]);
    assert.equal((await colors(page.locator(".online-order-channel-actions .primary-action"))).color, black);

    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 390);
    assert.equal(await page.locator(".portal-nav-group-title").first().evaluate((element) => getComputedStyle(element).borderBottomWidth), "1px");
    assert.equal(await page.locator(".portal-sidebar .sidebar-menu-item strong").first().evaluate((element) => getComputedStyle(element).whiteSpace), "nowrap");
    await page.goto(`${base}/online/orders/process`);
    const disabled = page.locator(".online-order-panel .primary-action").first();
    await disabled.waitFor();
    assert.equal((await colors(disabled)).background, "rgb(229, 231, 235)");

    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(`${base}/online/recall`);
    const activeTab = page.locator(".online-recall-tabs button.active");
    await activeTab.waitFor();
    assert.equal((await colors(activeTab)).background, black);
    assert.equal((await colors(activeTab)).color, white);

    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 390);
    await page.goto(`${base}/assets`);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), 390);
    await page.setViewportSize({ width: 1280, height: 800 });

    await page.goto(`${base}/settings`);
    await page.getByRole("button", { name: /관리자 설정/ }).click();
    await page.getByRole("button", { name: "관리자 비밀번호 초기화" }).click();
    const danger = page.locator(".admin-reset-submit");
    await danger.waitFor();
    assert.equal((await colors(danger)).color, "rgb(220, 38, 38)");
    assert.equal((await colors(danger)).border, "rgb(220, 38, 38)");
    await danger.hover();
    await page.waitForTimeout(450);
    assert.equal((await colors(danger)).color, white);
    assert.equal((await colors(page.locator(".admin-auth-modal-actions .secondary-button"))).background, white);

    mockUser = { id: 2, username: "member", name: "일반 사용자", role: "user", menu_permissions: ["online_home"], is_active: true };
    await page.goto(`${base}/online`);
    await page.locator('.portal-sidebar .sidebar-menu-item[aria-current="page"]').waitFor();
    assert.equal(await page.locator(".portal-sidebar .sidebar-menu-item").count(), 1);
    assert.equal(await page.locator(".sidebar-edit-button").count(), 0);
  } finally {
    await context.close();
    await browser.close();
    await vite.close();
  }
});
