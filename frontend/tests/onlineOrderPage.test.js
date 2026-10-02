import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import { MENU_GROUPS, MENU_ITEMS_BY_ID } from "../src/config/menuDefinitions.js";
import { canAccessSection, getAllowedSectionIds } from "../src/utils/menuPermissions.js";

test("발주 관리 메뉴는 리콜 관리 다음에 있고 사용자 권한을 따른다", () => {
  const onlineGroup = MENU_GROUPS.find((group) => group.title === "온라인 TEAM");
  assert.deepEqual(onlineGroup.itemIds, ["online-home", "online-recall", "online-order"]);
  assert.equal(MENU_ITEMS_BY_ID["online-order"].menuKey, "online_order");
  assert.equal(MENU_ITEMS_BY_ID["online-order"].routePath, "/online/orders");

  const visible = { online_order: true };
  assert.equal(canAccessSection("online-order", visible, new Set(), true), true);
  assert.equal(canAccessSection("online-order", visible, new Set(), false), false);
  assert.equal(canAccessSection("online-order", visible, new Set(getAllowedSectionIds(["online_order"])), false), true);
  assert.equal(canAccessSection("online-order", { online_order: false }, new Set(getAllowedSectionIds(["online_order"])), false), false);
});

test("발주 관리 페이지와 기존 온라인 페이지가 렌더링된다", async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
  try {
    const { default: OrderManagementPage } = await vite.ssrLoadModule("/src/components/online/OrderManagementPage.jsx");
    const { default: OnlineTeamHomePage } = await vite.ssrLoadModule("/src/components/online/OnlineTeamHomePage.jsx");
    const { default: RecallManagementPage } = await vite.ssrLoadModule("/src/components/online/RecallManagementPage.jsx");
    const html = renderToStaticMarkup(React.createElement(OrderManagementPage));
    assert.match(html, /발주 관리/);
    assert.match(html, /준비 중/);
    assert.match(renderToStaticMarkup(React.createElement(OnlineTeamHomePage)), /온라인 TEAM/);
    assert.match(renderToStaticMarkup(React.createElement(RecallManagementPage)), /리콜 관리/);

    const appSource = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
    assert.match(appSource, /activeSection === "online-order"[\s\S]*?return <OrderManagementPage \/>/);
  } finally {
    await vite.close();
  }
});
