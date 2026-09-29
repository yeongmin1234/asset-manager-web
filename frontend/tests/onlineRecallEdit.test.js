import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("detail header switches between edit and save actions", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { RecallDetailHeaderActions } = await vite.ssrLoadModule("/src/components/online/RecallDetailModal.jsx");
    const render = (props) => renderToStaticMarkup(React.createElement(RecallDetailHeaderActions, { canEdit: true, editing: false, saving: false, ...props }));
    const read = render();
    assert.match(read, /수정/);
    assert.match(read, /닫기/);
    assert.doesNotMatch(read, /저장/);
    const edit = render({ editing: true });
    assert.match(edit, /저장/);
    assert.match(edit, /취소/);
    assert.doesNotMatch(edit, /닫기/);
    assert.match(render({ editing: true, saving: true }), /disabled=""/);
    assert.doesNotMatch(render({ canEdit: false }), /수정/);
  } finally {
    await vite.close();
  }
});

test("detail edit sends only the supplied application fields to the shared update API", async () => {
  const previousWindow = globalThis.window;
  const previousFetch = globalThis.fetch;
  let request;
  globalThis.window = {
    setTimeout, clearTimeout,
    location: { hostname: "127.0.0.1", protocol: "http:" },
    localStorage: { getItem: () => "token" },
  };
  globalThis.fetch = async (url, options) => {
    request = { url: String(url), options };
    return { ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => ({ changed: true }) };
  };
  try {
    const { updateRecallApplication } = await import("../src/api/client.js");
    const fields = { customer_name: "수정 고객", phone_original: "011 1234 5678" };
    assert.deepEqual(await updateRecallApplication(42, fields), { changed: true });
    assert.match(request.url, /\/online\/recall\/applications\/42$/);
    assert.equal(request.options.method, "PATCH");
    assert.deepEqual(JSON.parse(request.options.body), fields);
    assert.equal(request.options.headers.Authorization, "Bearer token");
  } finally {
    globalThis.window = previousWindow;
    globalThis.fetch = previousFetch;
  }
});
