import test from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("current visitors show names only while count and server states remain visible", async () => {
  const vite = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: ServerStatusPopover } = await vite.ssrLoadModule("/src/components/ServerStatusPopover.jsx");
    const html = renderToStaticMarkup(React.createElement(ServerStatusPopover, {
      isOpen: true,
      showVisitorSummary: true,
      status: { type: "ok", backendOk: true, dbOk: true },
      visitorSummary: {
        active_count: 2,
        active_window_seconds: 180,
        visitors: [
          { user_name: "더리모 관리자", ip_address: "192.168.222.11", user_agent: "Chrome/120", last_seen: "2026-09-29T02:16:19Z" },
          { user_name: "신성아", ip_address: "192.168.222.12", user_agent: "Firefox/120", last_seen: "2026-09-29T02:16:20Z" },
        ],
      },
    }));
    assert.match(html, /현재 접속 2명/);
    assert.match(html, /최근 180초 기준/);
    assert.match(html, /Backend API/);
    assert.match(html, /DB 연결/);
    assert.match(html, /Frontend/);
    assert.match(html, /더리모 관리자/);
    assert.match(html, /신성아/);
    assert.doesNotMatch(html, /192\.168\.222|Chrome|Firefox|02:16:19|visitor-browser|visitor-meta/);
    const unnamed = renderToStaticMarkup(React.createElement(ServerStatusPopover, {
      isOpen: true, showVisitorSummary: true, status: { type: "ok" },
      visitorSummary: { active_count: 1, visitors: [{ ip_address: "10.1.2.3", user_agent: "Chrome/120" }] },
    }));
    assert.match(unnamed, /알 수 없음/);
    assert.doesNotMatch(unnamed, /10\.1\.2\.3|Chrome/);
  } finally {
    await vite.close();
  }
});
