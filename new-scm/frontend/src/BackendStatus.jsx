import React, { useEffect, useState } from "react";
import { getSystemStatus } from "./services/systemService";

export default function BackendStatus() {
  const [state, setState] = useState("확인 중");
  useEffect(() => {
    let active = true;
    getSystemStatus().then(
      () => { if (active) setState("연결됨"); },
      () => { if (active) setState("연결 안 됨"); }
    );
    return () => { active = false; };
  }, []);
  return (
    <div role="status" aria-live="polite" style={{padding:"6px 16px",fontSize:"12px",textAlign:"right"}}>
      신규 SCM API: {state} · DB 상태는 별도 점검
    </div>
  );
}
