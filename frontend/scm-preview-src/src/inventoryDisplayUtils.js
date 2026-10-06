export const formatQuantity = (value) => Number(value).toLocaleString("ko-KR", { maximumFractionDigits: 10 });
export const sortWarehouses = (rows, sort) => [...rows].sort((a, b) => {
  if (sort === "quantity-asc") return a.quantity - b.quantity;
  if (sort === "name-asc") return a.warehouse_name.localeCompare(b.warehouse_name, "ko");
  if (sort === "name-desc") return b.warehouse_name.localeCompare(a.warehouse_name, "ko");
  return b.quantity - a.quantity;
});
