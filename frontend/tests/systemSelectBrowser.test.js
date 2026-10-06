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

test("로그인 후 시스템 선택과 역할별 접근, 전환 및 로그아웃", { skip: !browserPath || !existsSync(browserPath) }, async () => {
  const vite = await createServer({ server: { host: "127.0.0.1", port: 0, hmr: false } });
  await vite.listen();
  const base = `http://127.0.0.1:${vite.httpServer.address().port}`;
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const page = await browser.newPage();
  const errors = [];
  let role = "admin";
  let permissions = ["dashboard", "assets"];
  const user = () => ({ id: 1, username: "tester", name: "테스트 사용자", role, menu_permissions: permissions, is_active: true });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("http://127.0.0.1:8010/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const body = pathname === "/auth/login"
      ? { access_token: "test-token", token_type: "bearer", user: user() }
      : pathname === "/auth/me"
        ? user()
        : pathname === "/menu-visibility"
          ? { visibility: {} }
          : {};
    await route.fulfill({ status: 200, contentType: "application/json", headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "*" }, body: JSON.stringify(body) });
  });
  const login = async () => {
    await page.locator(".login-form input[autocomplete=username]").fill("tester");
    await page.locator(".login-form input[autocomplete=current-password]").fill("password123");
    await page.getByRole("button", { name: "로그인", exact: true }).click();
    await page.waitForURL(`${base}/select-system`);
  };

  try {
    await page.goto(`${base}/dashboard`);
    await page.waitForURL(`${base}/login`);
    await login();
    assert.equal(await page.getByRole("button", { name: "자산관리 시스템 들어가기" }).count(), 1);
    assert.equal(await page.getByRole("button", { name: "SCM 시스템 들어가기" }).count(), 1);
    await page.reload();
    await page.waitForURL(`${base}/select-system`);
    await page.getByRole("button", { name: "자산관리 시스템 들어가기" }).click();
    await page.waitForURL(`${base}/dashboard`);
    await page.getByRole("button", { name: "시스템 선택", exact: true }).click();
    await page.getByRole("button", { name: "SCM 시스템 들어가기" }).click();
    await page.waitForURL(`${base}/scm-app`);
    await page.getByRole("button", { name: /시스템 선택/ }).click();
    await page.waitForURL(`${base}/select-system`);
    await page.getByRole("button", { name: "로그아웃" }).click();
    await page.waitForURL(`${base}/login`);

    role = "user";
    permissions = ["dashboard", "assets"];
    await login();
    assert.equal(await page.getByRole("button", { name: "SCM 시스템 접근 권한 없음" }).isDisabled(), true);
    await page.goto(`${base}/scm-app`);
    await page.getByText("SCM 시스템에 접근할 권한이 없습니다.").waitFor();
    await page.getByRole("button", { name: "시스템 선택으로 이동" }).click();
    await page.getByRole("button", { name: "로그아웃" }).click();
    await page.waitForURL(`${base}/login`);

    permissions = ["scm_app"];
    await login();
    assert.equal(await page.getByRole("button", { name: "자산관리 시스템 접근 권한 없음" }).isDisabled(), true);
    await page.getByRole("button", { name: "SCM 시스템 들어가기" }).click();
    await page.waitForURL(`${base}/scm-app`);
    await page.reload();
    await page.locator(".scm-site-frame").waitFor();
    await page.getByRole("button", { name: "로그아웃" }).click();
    await page.waitForURL(`${base}/login`);

    for (const routePath of ["/select-system", "/scm-app", "/dashboard"]) {
      await page.goto(`${base}${routePath}`);
      await page.waitForURL(`${base}/login`);
      await page.locator(".login-form").waitFor();
    }
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
    await vite.close();
  }
});
