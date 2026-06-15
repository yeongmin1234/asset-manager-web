import React from "react";

const STATUS_LABELS = {
  "사용중": "in-use",
  미사용: "unused",
  폐기: "disposed",
};

function StatusBadge({ status }) {
  const className = STATUS_LABELS[status] || "unknown";

  return <span className={`status-badge status-badge-${className}`}>{status}</span>;
}

export default StatusBadge;
