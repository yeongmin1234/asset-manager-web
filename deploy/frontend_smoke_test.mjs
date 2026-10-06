import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const requireFromFrontend = createRequire(new URL("../frontend/package.json", import.meta.url));
const { chromium } = requireFromFrontend("playwright-core");
const args = process.argv.slice(2);
const checkBrowserOnly = args.includes("--check-browser");
const urlArg = args.indexOf("--url");
const targetUrl = urlArg >= 0 ? args[urlArg + 1] : args.find((arg) => /^https?:\/\//.test(arg)) || process.env.FRONTEND_SMOKE_URL || "http://127.0.0.1:3010/";
const cdpUrl = process.env.FRONTEND_SMOKE_CDP_URL;
const timeoutMs = Number(process.env.FRONTEND_SMOKE_TIMEOUT_MS || 20000);
const assetType = new Set(["document", "script", "stylesheet"]);

function browserPath() {
  const configured = process.env.FRONTEND_SMOKE_BROWSER_PATH;
  if (configured) return existsSync(configured) ? configured : null;
  const candidates = process.platform === "win32"
    ? [
        path.join(process.env.PROGRAMFILES || "C:\\Program Files", "Google/Chrome/Application/chrome.exe"),
        path.join(process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)", "Microsoft/Edge/Application/msedge.exe"),
      ]
    : ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable"];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
    if (process.platform !== "win32") {
      for (const directory of (process.env.PATH || "").split(path.delimiter)) {
        const resolved = path.join(directory, candidate);
        if (existsSync(resolved)) return resolved;
      }
    }
  }
  return null;
}

function isIgnorableConsoleError(message) {
  return /\/favicon\.ico(?:\?|$)/i.test(message.location().url || message.text());
}

async function main() {
  console.log("== Frontend browser smoke test ==");
  const executablePath = cdpUrl ? null : browserPath();
  if (!cdpUrl && !executablePath) {
    throw new Error("Chromium/Chrome executable missing. Set FRONTEND_SMOKE_BROWSER_PATH to an installed browser.");
  }
  console.log(`OK Browser: ${cdpUrl ? "remote Chromium via CDP" : executablePath}`);
  const openBrowser = () => cdpUrl
    ? chromium.connectOverCDP(cdpUrl, { timeout: timeoutMs })
    : chromium.launch({ executablePath, headless: true, args: ["--disable-dev-shm-usage"] });
  if (checkBrowserOnly) {
    const probe = await openBrowser();
    await probe.close();
    console.log("OK Headless browser launch");
    return;
  }
  if (!targetUrl || !/^https?:\/\//.test(targetUrl)) throw new Error("A valid --url or FRONTEND_SMOKE_URL is required.");

  const browser = await openBrowser();
  const page = await browser.newPage();
  const pageErrors = [];
  const consoleErrors = [];
  const assetFailures = [];
  page.on("pageerror", (error) => pageErrors.push(error.stack || error.message));
  page.on("console", (message) => {
    if (message.type() === "error" && !isIgnorableConsoleError(message)) consoleErrors.push(`${message.text()} ${message.location().url || ""}`.trim());
  });
  page.on("requestfailed", (request) => {
    if (assetType.has(request.resourceType())) assetFailures.push(`${request.url()}: ${request.failure()?.errorText || "request failed"}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400 && assetType.has(response.request().resourceType())) {
      assetFailures.push(`${response.url()}: HTTP ${response.status()}`);
    }
  });

  try {
    const response = await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: timeoutMs });
    if (!response || response.status() !== 200) throw new Error(`Frontend HTTP status: ${response?.status() || "no response"}`);
    console.log("OK HTTP status: 200");
    if (pageErrors.length) throw new Error(`JavaScript runtime error: ${pageErrors[0]}`);
    await page.waitForFunction(() => {
      const root = document.querySelector("#root");
      return root?.firstElementChild && (root.textContent || "").trim().length >= 8 &&
        (root.querySelector(".login-page .login-form") || root.querySelector(".portal-shell .portal-sidebar"));
    }, null, { timeout: timeoutMs });
    await page.waitForTimeout(750);
    const state = await page.evaluate(() => ({
      readyState: document.readyState,
      rootChildren: document.querySelector("#root")?.children.length || 0,
      rootTextLength: (document.querySelector("#root")?.textContent || "").trim().length,
      hasLogin: Boolean(document.querySelector("#root .login-page .login-form")),
      hasApp: Boolean(document.querySelector("#root .portal-shell .portal-sidebar")),
    }));
    if (!['interactive', 'complete'].includes(state.readyState)) throw new Error(`document.readyState: ${state.readyState}`);
    if (!state.rootChildren || state.rootTextLength < 8) throw new Error("React root is empty or has no meaningful text.");
    if (!state.hasLogin && !state.hasApp) throw new Error("Login form or app shell was not rendered.");
    console.log(`OK Root rendered (${state.rootTextLength} characters)`);
    console.log(`OK ${state.hasLogin ? "Login form" : "App shell"} detected`);
    if (pageErrors.length || consoleErrors.length || assetFailures.length) {
      throw new Error([
        ...pageErrors.map((error) => `JavaScript runtime error: ${error}`),
        ...consoleErrors.map((error) => `console.error: ${error}`),
        ...assetFailures.map((error) => `Core resource failed: ${error}`),
      ].join("\n"));
    }
    console.log("OK No page errors, fatal console errors, or core resource failures");
    console.log("PASS Frontend browser smoke test");
  } catch (error) {
    const details = [
      error.message,
      ...pageErrors.map((value) => `JavaScript runtime error: ${value}`),
      ...consoleErrors.map((value) => `console.error: ${value}`),
      ...assetFailures.map((value) => `Core resource failed: ${value}`),
    ];
    throw new Error([...new Set(details)].join("\n"));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`FAIL Frontend browser smoke test\n${error.message}\nFrontend deployment validation failed.`);
  process.exitCode = 1;
});
