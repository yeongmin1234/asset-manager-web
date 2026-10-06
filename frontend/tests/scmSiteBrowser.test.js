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

test("SCM 사이트 경로, 기존 SCM 보호, 인증과 메뉴 이동", { skip: !browserPath || !existsSync(browserPath) }, async () => {
  const vite = await createServer({ server: { host: "127.0.0.1", port: 0, hmr: false } });
  await vite.listen();
  const base = `http://127.0.0.1:${vite.httpServer.address().port}`;
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  const errors = [];
  let role = "admin";
  page.on("pageerror", (error) => errors.push(error.message));
  await context.addInitScript(() => localStorage.setItem("assetManager.accessToken", "test-token"));
  await page.route("http://127.0.0.1:8010/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const body = pathname === "/auth/me"
      ? { id: 1, username: "test", name: "테스트 관리자", role, menu_permissions: ["dashboard", "assets"], is_active: true }
      : pathname === "/menu-visibility"
        ? { visibility: { online_home: true } }
        : {};
    await route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "*" }, body: JSON.stringify(body) });
  });

  try {
    await page.goto(`${base}/dashboard`);
    await page.getByRole("button", { name: /SCM 시스템/ }).click();
    await page.waitForURL(`${base}/scm-app`);
    assert.equal(await page.locator(".portal-sidebar").count(), 0);
    assert.equal(await page.getByText("The Limo & SCM").count(), 1);
    const frame = page.frameLocator(".scm-site-frame");
    await frame.getByRole("navigation", { name: "주요 메뉴" }).getByText("매장관리").click();
    await page.waitForURL(`${base}/scm-app/stores/staff`);
    await page.reload();
    await frame.getByRole("navigation", { name: "주요 메뉴" }).getByText("매장관리").waitFor();
    await page.goBack();
    await page.waitForURL(`${base}/scm-app`);
    await page.getByRole("button", { name: /시스템 선택/ }).click();
    await page.waitForURL(`${base}/select-system`);
    await page.getByRole("button", { name: "자산관리 시스템 들어가기" }).click();
    await page.waitForURL(`${base}/dashboard`);
    for (const routePath of ["/assets", "/online"]) {
      await page.goto(`${base}${routePath}`);
      await page.locator(".portal-shell").waitFor();
      assert.equal(new URL(page.url()).pathname, routePath);
    }
    await page.goto(`${base}/scm`);
    await page.getByText("SCM MariaDB 관리").waitFor();
    for (const routePath of ["/scm-app/home", "/scm-app/stores", "/scm-app/customers", "/scm-app/consultations", "/scm-app/as", "/scm-app/sales", "/scm-app/logistics", "/scm-app/order-support", "/scm-app/notices", "/scm-app/memo-search", "/scm-app/settings"]) {
      await page.goto(`${base}${routePath}`);
      await page.locator(".scm-site-frame").waitFor();
      assert.equal(new URL(page.url()).pathname, routePath);
    }
    await page.goto(`${base}/scm-preview/index.html`);
    await page.waitForURL(`${base}/scm-app`);

    role = "user";
    await page.goto(`${base}/scm-app/home`);
    await page.getByText("접근 권한이 없습니다.").waitFor();
    assert.equal(await page.locator(".scm-site-frame").count(), 0);

    const anonymous = await browser.newPage();
    try {
      await anonymous.goto(`${base}/scm-app/home`);
      await anonymous.waitForSelector(".login-form");
      await anonymous.goto(`${base}/scm-preview/index.html`);
      await anonymous.waitForURL(`${base}/login`);
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
