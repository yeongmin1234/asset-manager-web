import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { chromium } from "playwright-core";
import { createServer } from "vite";

const browserPath = process.env.FRONTEND_SMOKE_BROWSER_PATH || (
  process.platform === "win32"
    ? path.join(process.env.PROGRAMFILES || "C:\\Program Files", "Google/Chrome/Application/chrome.exe")
    : ["/usr/bin/chromium", "/usr/bin/google-chrome"].find(existsSync)
);

test("발주 하위 경로 직접 접속, 새로고침, 뒤로가기와 기존 메뉴 이동", { skip: !browserPath || !existsSync(browserPath) }, async () => {
  const vite = await createServer({ server: { host: "127.0.0.1", port: 0, hmr: false } });
  await vite.listen();
  const port = vite.httpServer.address().port;
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  const errors = [];
  let userRole = "user";
  let userPermissions = ["dashboard", "online_home", "online_order"];
  page.on("pageerror", (error) => errors.push(error.message));
  await context.addInitScript(() => localStorage.setItem("assetManager.accessToken", "test-token"));
  await page.route("http://127.0.0.1:8010/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const body = pathname === "/auth/me"
      ? { id: 1, username: "order-user", name: "발주 담당자", role: userRole, menu_permissions: userPermissions, is_active: true }
      : pathname === "/menu-visibility"
        ? { visibility: { online_home: true, online_order: true, online_recall: true } }
        : pathname === "/online/orders/channels"
          ? [{ id: 1, name: "스마트스토어", code: "smartstore", is_active: true, is_default: true, processing_supported: false }]
        : {};
    await route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "*" }, body: JSON.stringify(body) });
  });

  try {
    const base = `http://127.0.0.1:${port}`;
    await page.goto(`${base}/online/orders/process`);
    await page.waitForSelector(".online-order-page #online-order-file");
    assert.equal(new URL(page.url()).pathname, "/online/orders/process");
    await page.reload();
    await page.waitForSelector(".online-order-page #online-order-file");
    await page.locator('.online-order-nav button', { hasText: "결과 미리보기" }).click();
    assert.equal(new URL(page.url()).pathname, "/online/orders/preview");
    await page.goBack();
    await page.waitForSelector(".online-order-page #online-order-file");
    assert.equal(new URL(page.url()).pathname, "/online/orders/process");
    await page.goForward();
    await page.waitForSelector(".online-order-skeleton-table");
    assert.equal(new URL(page.url()).pathname, "/online/orders/preview");
    await page.getByRole("button", { name: "대시보드로 이동" }).click();
    assert.equal(new URL(page.url()).pathname, "/dashboard");
    for (const routePath of ["/online/orders", "/online/orders/mappings", "/online/orders/history", "/online/orders/settings"]) {
      await page.goto(`${base}${routePath}`);
      await page.waitForSelector(".online-order-page");
      assert.equal(new URL(page.url()).pathname, routePath);
    }
    userPermissions = ["dashboard"];
    await page.reload();
    await page.waitForSelector(".access-denied-card");
    userRole = "admin";
    await page.reload();
    await page.waitForSelector(".online-order-page");
    const anonymous = await browser.newPage();
    try {
      await anonymous.goto(`${base}/online/orders`);
      await anonymous.waitForSelector(".login-form");
    } finally {
      await anonymous.close();
    }
    assert.deepEqual(errors, []);
  } finally {
    await context.close();
    await browser.close();
    await vite.close();
  }
});
