import React, { useCallback, useEffect, useState } from "react";
import { dryRunScmReboot, getScmServerStatus } from "../api/client.js";
import ScmRebootDryRunPanel from "./ScmRebootDryRunPanel.jsx";
import ScmRebootProgressModal from "./ScmRebootProgressModal.jsx";
import ScmServerStatus from "./ScmServerStatus.jsx";

function ScmPage() {
  const [status, setStatus] = useState(null);
  const [statusState, setStatusState] = useState({ isLoading: false, error: "" });
  const [progressModal, setProgressModal] = useState({
    isOpen: false,
    runKey: 0,
  });

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

  const handleDryRunSuccess = () => {
    setProgressModal((current) => ({
      isOpen: true,
      runKey: current.runKey + 1,
    }));
  };

  const handleProgressClose = () => {
    setProgressModal((current) => ({
      ...current,
      isOpen: false,
    }));
  };

  return (
    <section className="scm-page" aria-labelledby="scm-page-title">
      <div className="portal-screen-heading scm-page-heading">
        <div>
          <span className="section-kicker">Server Operations</span>
          <h2 id="scm-page-title">SCM 서버 관리</h2>
          <p>SCM 서버 상태를 확인하고, 안전한 재부팅 절차를 준비합니다.</p>
        </div>
      </div>

      <ScmServerStatus
        status={status}
        isLoading={statusState.isLoading}
        error={statusState.error}
        onRefresh={loadStatus}
      />

      <ScmRebootDryRunPanel onDryRun={dryRunScmReboot} onDryRunSuccess={handleDryRunSuccess} />

      <ScmRebootProgressModal
        isOpen={progressModal.isOpen}
        runKey={progressModal.runKey}
        onClose={handleProgressClose}
        onRefreshStatus={loadStatus}
        isRefreshingStatus={statusState.isLoading}
      />
    </section>
  );
}

export default ScmPage;
