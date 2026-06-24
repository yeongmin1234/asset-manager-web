import React, { useCallback, useEffect, useState } from "react";
import { dryRunScmMariaDbRestart, getScmServerStatus } from "../api/client.js";
import ScmEmergencyGuide from "./ScmEmergencyGuide.jsx";
import ScmMariaDbPanel from "./ScmMariaDbPanel.jsx";
import ScmServerStatus from "./ScmServerStatus.jsx";

function ScmPage() {
  const [status, setStatus] = useState(null);
  const [statusState, setStatusState] = useState({ isLoading: false, error: "" });

  const loadStatus = useCallback(async () => {
    setStatusState({ isLoading: true, error: "" });
    try {
      const data = await getScmServerStatus();
      setStatus(data);
      setStatusState({ isLoading: false, error: "" });
    } catch (error) {
      setStatus(null);
      setStatusState({ isLoading: false, error: error.message });
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  return (
    <section className="scm-page" aria-labelledby="scm-page-title">
      <div className="portal-screen-heading scm-page-heading">
        <div>
          <span className="section-kicker">Server Operations</span>
          <h2 id="scm-page-title">SCM MariaDB 관리</h2>
          <p>SCM 서버의 MariaDB 상태와 3306 포트를 확인하고, 긴급 복구 절차를 준비합니다.</p>
        </div>
      </div>

      <ScmServerStatus
        status={status}
        isLoading={statusState.isLoading}
        error={statusState.error}
        onRefresh={loadStatus}
      />

      <div className="scm-work-grid">
        <ScmMariaDbPanel onDryRun={dryRunScmMariaDbRestart} />
        <ScmEmergencyGuide />
      </div>
    </section>
  );
}

export default ScmPage;
