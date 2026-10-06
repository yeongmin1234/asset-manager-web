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
    await page.route("http://127.0.0.1:8010/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      const body = pathname === "/auth/me"
        ? { id: 1, username: "admin", name: "관리자", role: "admin", menu_permissions: [], is_active: true }
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
  } finally {
    await context.close();
    await browser.close();
    await vite.close();
  }
});
