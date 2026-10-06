export const ORDER_MANAGEMENT_ROUTES = [
  { path: "/online/orders", label: "발주 대시보드", page: "dashboard" },
  { path: "/online/orders/process", label: "발주 파일 가공", page: "process" },
  { path: "/online/orders/preview", label: "결과 미리보기", page: "preview" },
  { path: "/online/orders/mappings", label: "상품 매칭 관리", page: "mappings" },
  { path: "/online/orders/history", label: "가공 이력", page: "history" },
  { path: "/online/orders/settings", label: "설정", page: "settings" },
];

export function isOrderManagementPath(path) {
  return ORDER_MANAGEMENT_ROUTES.some((route) => route.path === path);
}
