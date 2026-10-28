import test from "node:test";
import assert from "node:assert/strict";
import { authRequest, login, logout, restoreSession } from "../src/services/authService.js";
import { canAccessPath, canPerform } from "../src/constants/permissions.js";

test("independent login sends only SCM credentials to same origin, with cookie support", async () => {
  let call;
  globalThis.fetch = async (...args) => { call = args; return { ok: true, json: async () => ({ data: { authenticated: true } }) }; };
  assert.deepEqual(await login("test-user", "test-only-password"), { authenticated: true });
  assert.equal(call[0], "/api/v1/auth/login");
  assert.equal(call[1].credentials, "include");
  assert.equal(call[1].cache, "no-store");
  assert.deepEqual(JSON.parse(call[1].body), { username: "test-user", password: "test-only-password" });
});

test("session restoration maps server grants without a handoff or bearer token", async () => {
  let path;
  globalThis.fetch = async url => { path = url; return { ok: true, json: async () => ({ ok: true,
    data: { subject: "2", account_type: "employee", action_grants: ["system.access"] } }) }; };
  const user = await restoreSession();
  assert.equal(path, "/api/v1/auth/me"); assert.equal(user.accountType, "employee");
  globalThis.fetch = async () => ({ ok: false, status: 401 });
  assert.equal(await restoreSession(), null);
});

test("logout requires a successful server revocation response", async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "/api/v1/auth/logout"); assert.equal(options.method, "POST");
    return { ok: true, json: async () => ({ data: { logged_out: true } }) };
  };
  assert.deepEqual(await logout(), { logged_out: true });
  globalThis.fetch = async () => ({ ok: false, status: 503 });
  await assert.rejects(logout(), error => error.status === 503);
});

test("401 clears authentication through a fixed event; response details are never exposed", async () => {
  let event;
  globalThis.window = { dispatchEvent: value => { event = value; } };
  globalThis.fetch = async () => ({ ok: false, status: 401, text: async () => "private-test-value" });
  await assert.rejects(authRequest("/admin/auth/users"), error => error.status === 401 && error.message === "auth_request_failed");
  assert.equal(event.type, "scm-session-expired");
});

test("normal users cannot open admin menus or acquire absent action grants", () => {
  const user = { status: "active", account_type: "employee", menu_grants: ["/sales", "/settings/accounts"],
    action_grants: ["system.access", "data.read", "admin.manage"] };
  assert.equal(canAccessPath(user, "/sales"), true);
  assert.equal(canAccessPath(user, "/settings/accounts"), false);
  assert.equal(canPerform(user, "read"), true); assert.equal(canPerform(user, "delete"), false);
  assert.equal(canAccessPath({ ...user, status: "suspended" }, "/sales"), false);
});

test("admin access still requires explicit menu and system grants", () => {
  const admin = { status: "active", account_type: "admin", menu_grants: ["/settings/accounts"],
    action_grants: ["system.access", "admin.manage"] };
  assert.equal(canAccessPath(admin, "/settings/accounts"), true);
  assert.equal(canAccessPath(admin, "/settings/codes"), false);
  assert.equal(canAccessPath({ ...admin, action_grants: ["admin.manage"] }, "/settings/accounts"), false);
});
