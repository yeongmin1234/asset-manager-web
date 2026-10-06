import React, { useEffect, useState } from "react";
import { getSkoomiImage, SKOOMI_STATES, skoomiImages } from "./skoomiAssets";
import "./SkoomiMascot.css";

const stateAlt = {
  default: "업무를 안내하는 스쿠미",
  searching: "재고를 조회 중인 스쿠미",
  success: "조회 결과를 안내하는 스쿠미",
  guide: "품목 선택을 안내하는 스쿠미",
  empty: "빈 결과를 안내하는 스쿠미",
  error: "오류를 안내하는 스쿠미",
};

export default function SkoomiMascot({
  state = "default",
  size = "medium",
  message = "",
  alt,
  showMessage = true,
  className = "",
  decorative = false,
  compact = false,
  animate = true,
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const safeState = SKOOMI_STATES.includes(state) ? state : "default";
  const image = getSkoomiImage(safeState, size);
  const resolvedAlt = decorative ? "" : (alt ?? stateAlt[safeState] ?? stateAlt.default);

  useEffect(() => {
    setImageFailed(false);
  }, [image]);

  useEffect(() => {
    Object.values(skoomiImages).forEach((source) => {
      const preload = new Image();
      preload.src = source;
    });
  }, []);

  return (
    <div
      className={`skoomi-mascot skoomi-mascot--${size} skoomi-mascot--${safeState}${compact ? " skoomi-mascot--compact" : ""}${animate ? " skoomi-mascot--animated" : ""} ${className}`.trim()}
      role={message && showMessage && safeState === "error" ? "alert" : message && showMessage ? "status" : undefined}
      aria-live={message && showMessage ? (safeState === "error" ? "assertive" : "polite") : undefined}
    >
      <span className="skoomi-mascot__visual" aria-hidden={imageFailed ? "true" : undefined}>
        {!imageFailed && (
        <img
          key={safeState}
          src={image}
          alt={resolvedAlt}
          aria-hidden={decorative ? "true" : undefined}
          loading={size === "large" ? "eager" : "lazy"}
          onError={() => setImageFailed(true)}
        />
        )}
      </span>
      {showMessage && message && <p>{message}</p>}
    </div>
  );
}
