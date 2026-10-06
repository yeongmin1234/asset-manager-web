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
  let dashboardReads = 0;
  const recordedActions = [];
  let role = "admin";
  page.on("pageerror", (error) => errors.push(error.message));
  await context.addInitScript(() => localStorage.setItem("assetManager.accessToken", "test-token"));
  await page.route("http://127.0.0.1:8010/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/scm/dashboard") dashboardReads += 1;
    if (pathname === "/scm/activity" && route.request().method() === "POST") recordedActions.push(route.request().postDataJSON());
    const body = pathname === "/auth/me"
      ? { id: 1, username: "test", name: "테스트 관리자", role, menu_permissions: ["dashboard", "assets"], is_active: true }
      : pathname === "/menu-visibility"
        ? { visibility: { online_home: true } }
        : pathname === "/scm/dashboard"
          ? { recent_activity: [{ id: 1, user_name: "테스트 관리자", module: "sales", action: "create", message: "판매 등록 (미리보기)", created_at: "2026-10-06T16:42:00+09:00" }] }
          : pathname === "/scm/activity"
            ? { items: [{ id: 1, user_name: "테스트 관리자", module: "sales", action: "create", message: "판매 등록 (미리보기)", created_at: "2026-10-06T16:42:00+09:00" }], total: 1 }
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
    await frame.getByRole("heading", { name: "최근 작업 기록" }).waitFor();
    await frame.getByText("판매 등록 (미리보기)").waitFor();
    await new Promise((resolve) => setTimeout(resolve, 15500));
    assert.ok(dashboardReads >= 2, "HOME이 15초 후 작업 기록을 다시 조회해야 합니다.");
    await frame.getByRole("button", { name: "전체 이력 보기" }).click();
    await page.waitForURL(`${base}/scm-app/activity`);
    await frame.getByRole("heading", { name: "전체 작업 이력" }).waitFor();
    await frame.getByLabel("모듈").selectOption("sales");
    await frame.getByRole("button", { name: "검색" }).click();
    assert.ok(dashboardReads >= 1);
    await frame.getByRole("navigation", { name: "주요 메뉴" }).getByText("상담목록").click();
    await frame.getByRole("button", { name: "상담등록" }).click();
    const dialog = frame.getByRole("dialog", { name: "신규 상담등록" });
    await dialog.locator(".consult-create-field").filter({ hasText: "고객명" }).locator("input").fill("테스트 고객");
    await dialog.locator(".consult-create-field").filter({ hasText: "핸드폰" }).locator("input").fill("01012345678");
    await dialog.locator("textarea").fill("민감 내용은 로그에서 제외");
    await Promise.all([
      page.waitForResponse((response) => new URL(response.url()).pathname === "/scm/activity" && response.request().method() === "POST"),
      dialog.getByRole("button", { name: "상담등록" }).click(),
    ]);
    assert.deepEqual(recordedActions.at(-1), { module: "consultation", action: "create" });
    await frame.getByRole("navigation", { name: "주요 메뉴" }).getByText("매장관리").click();
    await page.waitForURL(`${base}/scm-app/stores/staff`);
    await page.reload();
    await frame.getByRole("navigation", { name: "주요 메뉴" }).getByText("매장관리").waitFor();
    await page.goto(`${base}/scm-app`);
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
