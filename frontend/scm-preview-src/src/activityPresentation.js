export const moduleLabels = {
  store: "매장", customer: "고객", consultation: "상담", as: "A/S",
  sales: "판매", logistics: "물류", order: "발주",
};

export const actionLabels = {
  create: "등록", update: "수정", delete: "삭제", status_change: "상태 변경",
  cancel: "취소", dispatch: "출고 처리",
};

export function formatActivityTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(date);
}
