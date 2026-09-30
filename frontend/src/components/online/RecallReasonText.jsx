import React from "react";
import { formatRecallReasons } from "./recallReasonLabels.js";

export default function RecallReasonText({ reasons }) {
  const label = formatRecallReasons(reasons);
  return <span className="online-target-reason-text" title={label}>{label}</span>;
}
