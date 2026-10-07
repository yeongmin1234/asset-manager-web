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

test("user management lives in settings and keeps administrator actions", { skip: !browserPath || !existsSync(browserPath) }, async () => {
  const vite = await createServer({ server: { host: "127.0.0.1", port: 0, hmr: false } });
  await vite.listen();
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const context = await browser.newContext({ viewport: { width: 1700, height: 900 } });
  const page = await context.newPage();
  const base = `http://127.0.0.1:${vite.httpServer.address().port}`;
  let currentUser = { id: 1, username: "admin", name: "관리자", role: "admin", menu_permissions: [], is_active: true };
  let users = [
    { ...currentUser, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
    { id: 2, username: "member", name: "일반 사용자", role: "user", menu_permissions: ["dashboard", "assets"], is_active: true, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
  ];
  const userWrites = [];
  let userReads = 0;
  const recentLimits = [];

  try {
    await context.addInitScript(() => localStorage.setItem("assetManager.accessToken", "test-token"));
    await page.route("http://127.0.0.1:8010/**", async (route) => {
      const request = route.request();
      const pathname = new URL(request.url()).pathname;
      const method = request.method();
      let body;
      if (pathname === "/auth/me") body = currentUser;
      else if (pathname === "/menu-visibility") body = { visibility: Object.fromEntries(MENU_ITEMS.map((item) => [item.menuKey, true])) };
      else if (pathname === "/admin/status") body = { configured: true };
      else if (pathname === "/activity-logs/recent") {
        recentLimits.push(new URL(request.url()).searchParams.get("limit"));
        body = Array.from({ length: 5 }, (_, index) => ({ id: index + 1, menu_name: "자산 관리", action_type: "update", summary: `변경 ${index + 1}`, created_at: "2026-01-01T00:00:00Z" }));
      }
      else if (pathname === "/users" && method === "GET") {
        userReads += 1;
        body = users;
      } else if (pathname === "/users" && method === "POST") {
        const payload = request.postDataJSON();
        body = { ...payload, id: 3, is_active: true, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
        users = [...users, body];
        userWrites.push({ method, pathname, payload });
      } else if (/^\/users\/\d+$/.test(pathname) && method === "PUT") {
        const payload = request.postDataJSON();
        const id = Number(pathname.split("/").at(-1));
        body = { ...users.find((user) => user.id === id), ...payload, id };
        users = users.map((user) => user.id === id ? body : user);
        userWrites.push({ method, pathname, payload });
      } else body = { items: [], total: 0 };
      await route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "*" }, body: JSON.stringify(body) });
    });

    await page.goto(`${base}/settings`);
    await page.getByRole("button", { name: /운영 기준/ }).waitFor();
    assert.equal(await page.locator(".settings-page-header h1").textContent(), "설정");
    assert.equal(await page.locator(".settings-page-header p").textContent(), "시스템 운영, 사이드바 메뉴 및 관리자 기능을 관리합니다.");
    const managementGroup = page.locator(".portal-nav-group").filter({ has: page.locator(".portal-nav-group-title", { hasText: "관리" }) });
    assert.deepEqual(await managementGroup.locator(".sidebar-menu-item strong").allTextContents(), ["설정"]);
    await page.locator(".portal-content-settings .recent-activity-item").first().waitFor();
    assert.equal(await page.locator(".portal-content-settings .recent-activity-item").count(), 5);
    assert.equal(recentLimits.includes("5"), true);
    assert.equal(await page.locator(".portal-content-settings .recent-activity-list").evaluate((element) => getComputedStyle(element).overflowY), "auto");
    const desktopBoxes = await Promise.all([".settings-page-header", ".settings-side-nav", ".settings-detail-panel", ".portal-content-settings .portal-aside"].map(async (selector) => page.locator(selector).boundingBox()));
    assert.ok(desktopBoxes[0].y < desktopBoxes[1].y);
    assert.ok(desktopBoxes[1].x < desktopBoxes[2].x && desktopBoxes[2].x < desktopBoxes[3].x);
    assert.ok(desktopBoxes[1].width >= 238 && desktopBoxes[1].width <= 242);
    assert.ok(desktopBoxes[2].width >= 720);
    assert.ok(desktopBoxes[3].width >= 298 && desktopBoxes[3].width <= 302);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    const summaryBox = await page.locator(".settings-detail-heading").boundingBox();
    const contentBox = await page.locator(".settings-detail-content").boundingBox();
    assert.ok(contentBox.y > summaryBox.y + summaryBox.height);
    for (const selector of [".settings-detail-heading", ".settings-detail-content", ".portal-content-settings .portal-side-card"]) {
      const cardStyle = await page.locator(selector).evaluate((element) => ({
        background: getComputedStyle(element).backgroundColor,
        radius: getComputedStyle(element).borderRadius,
        padding: getComputedStyle(element).paddingTop,
      }));
      assert.deepEqual(cardStyle, { background: "rgb(255, 255, 255)", radius: "12px", padding: selector.includes("side-card") ? "20px" : "22px" });
    }
    const selectedMenuColors = await page.locator(".settings-nav-item.active").evaluate((element) => ({
      background: getComputedStyle(element).backgroundColor,
      color: getComputedStyle(element).color,
    }));
    assert.deepEqual(selectedMenuColors, { background: "rgb(17, 17, 17)", color: "rgb(255, 255, 255)" });
    await page.getByRole("button", { name: /메뉴 표시 설정/ }).click();
    await page.getByText("사이드바 표시 메뉴").first().waitFor();

    await page.getByRole("button", { name: /관리자 설정/ }).click();
    assert.deepEqual(await page.locator(".settings-protected-menu-groups h3").allTextContents(), ["시스템 관리", "업무 관리", "자산 / 전산", "시스템 기록"]);
    const softwareToggle = page.locator(".settings-protected-menu-groups label.settings-menu-toggle").filter({ hasText: "SW 현황" });
    await softwareToggle.locator("strong").click();
    assert.equal(await softwareToggle.locator("input").isChecked(), true);
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem("assetManager.protectedMenus")).software), true);
    await page.locator(".settings-protected-menu-groups .settings-menu-link-row").filter({ hasText: "사용자 관리" }).getByRole("button", { name: "열기" }).click();
    await page.waitForURL("**/settings?tab=users");
    await page.locator(".user-table tbody tr").filter({ hasText: "member" }).waitFor();
    assert.equal(await page.locator(".user-table tbody tr").count(), 2);
    await page.locator(".user-create-panel input[placeholder='ID']").fill("newuser");
    await page.locator(".user-create-panel input[placeholder='이름']").fill("새 사용자");
    await page.locator(".user-create-panel input[placeholder^='비밀번호']").fill("password123");
    await page.getByRole("button", { name: "사용자 생성" }).click();
    await page.locator(".user-table tbody tr").filter({ hasText: "newuser" }).waitFor();
    assert.equal(userWrites.some((item) => item.method === "POST" && item.pathname === "/users"), true);

    const memberRow = page.locator(".user-table tbody tr").filter({ hasText: "member" });
    await memberRow.locator("td:nth-child(2) input").fill("변경된 사용자");
    await memberRow.locator(".user-status-toggle input").uncheck();
    await memberRow.getByRole("button", { name: "저장", exact: true }).click();
    await page.getByText("사용자 정보를 수정했습니다.", { exact: true }).waitFor();
    assert.equal(userWrites.some((item) => item.method === "PUT" && item.pathname === "/users/2" && item.payload.name === "변경된 사용자" && item.payload.is_active === false), true);

    await page.getByRole("button", { name: "관리자 설정으로 돌아가기" }).click();
    await page.locator(".settings-protected-menu-groups .settings-menu-link-row").filter({ hasText: "메뉴 권한 관리" }).getByRole("button", { name: "열기" }).click();
    await page.waitForURL("**/settings?tab=permissions");
    assert.equal(await page.locator(".user-create-panel").count(), 0);
    await page.locator(".user-table tbody tr").filter({ hasText: "member" }).getByRole("button", { name: "메뉴 권한" }).click();
    const permissionDialog = page.getByRole("dialog", { name: "member 메뉴 권한" });
    await permissionDialog.waitFor();
    await permissionDialog.getByRole("checkbox", { name: "통계 / 리포트" }).check();
    await permissionDialog.getByRole("button", { name: "권한 저장" }).click();
    await permissionDialog.waitFor({ state: "hidden" });
    assert.equal(userWrites.some((item) => item.method === "PUT" && item.pathname === "/users/2" && item.payload.menu_permissions.includes("statistics")), true);
    await page.goBack();
    await page.waitForURL("**/settings");
    await page.locator(".settings-protected-menu-groups").waitFor();

    await page.goto(`${base}/admin/users`);
    await page.waitForURL("**/settings?tab=users");
    await page.locator(".user-create-panel").waitFor();

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${base}/settings`);
    const mobileBoxes = await Promise.all([".settings-page-header", ".settings-side-nav", ".settings-detail-panel", ".portal-content-settings .portal-aside"].map(async (selector) => page.locator(selector).boundingBox()));
    assert.ok(mobileBoxes[0].y < mobileBoxes[1].y && mobileBoxes[1].y < mobileBoxes[2].y && mobileBoxes[2].y < mobileBoxes[3].y);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
    await page.setViewportSize({ width: 900, height: 800 });
    const tabletBoxes = await Promise.all([".settings-detail-panel", ".portal-content-settings .portal-aside"].map(async (selector) => page.locator(selector).boundingBox()));
    assert.ok(tabletBoxes[0].y < tabletBoxes[1].y);
    await page.setViewportSize({ width: 2100, height: 900 });
    assert.ok((await page.locator(".portal-content-settings").boundingBox()).width <= 1600);

    currentUser = { id: 2, username: "member", name: "일반 사용자", role: "user", menu_permissions: ["dashboard"], is_active: true };
    const readsBeforeDenied = userReads;
    await page.goto(`${base}/settings?tab=users`);
    await page.getByText("접근 권한이 없습니다.", { exact: true }).waitFor();
    assert.equal(await page.locator(".settings-protected-menu-groups").count(), 0);
    assert.equal(userReads, readsBeforeDenied);
    await page.goto(`${base}/settings?tab=permissions`);
    await page.getByText("접근 권한이 없습니다.", { exact: true }).waitFor();
    assert.equal(userReads, readsBeforeDenied);
    await page.goto(`${base}/admin/users`);
    await page.getByText("접근 권한이 없습니다.", { exact: true }).waitFor();
    assert.equal(userReads, readsBeforeDenied);
  } finally {
    await context.close();
    await browser.close();
    await vite.close();
  }
});
