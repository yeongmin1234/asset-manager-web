import React, { useEffect, useState } from "react";

const SUCCESS_MESSAGE = "MariaDB 재시작 조건 확인이 완료되었습니다. 현재 단계에서는 실제 재시작 명령을 실행하지 않습니다.";
const DISABLED_MESSAGE =
  "현재 실제 MariaDB 재시작은 비활성화되어 있습니다. 기능 활성화는 담당 관리자에게 문의하세요.";
const FINAL_WARNING =
  "MariaDB를 재시작하면 SCM 웹/DB 접속이 잠시 중단될 수 있습니다. 업무 영향이 없는 시간에 실행하세요.";

const INITIAL_FORM = {
  admin_password: "",
  reason: "",
  confirm_text: "",
};

function ScmMariaDbPanel({ status, onDryRun, onRestart, onRefreshStatus }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);
  const [dryRunPassed, setDryRunPassed] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [restartResult, setRestartResult] = useState(null);
  const restartEnabled = Boolean(status?.mariadb_restart_enabled);
  const canExecuteRestart = restartEnabled && dryRunPassed && countdown === 0 && !isRestarting;

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setMessage({ type: "", text: "" });
    setDryRunPassed(false);
    setCountdown(0);
    setRestartResult(null);
  };

  useEffect(() => {
    if (!dryRunPassed || countdown <= 0) {
      return undefined;
    }
    const timer = window.setTimeout(() => {
      setCountdown((current) => Math.max(current - 1, 0));
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [countdown, dryRunPassed]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const reason = form.reason.trim();
    const confirmText = form.confirm_text.trim();
    if (!reason) {
      setMessage({ type: "error", text: "MariaDB 재시작 사유를 입력해주세요." });
      return;
    }
    if (confirmText !== "MARIADB") {
      setMessage({ type: "error", text: "확인 문구를 정확히 MARIADB로 입력해주세요." });
      return;
    }

    setIsSubmitting(true);
    setMessage({ type: "", text: "" });
    try {
      const result = await onDryRun({
        admin_password: form.admin_password,
        reason,
        confirm_text: confirmText,
      });
      setMessage({
        type: "success",
        text: result?.message || SUCCESS_MESSAGE,
      });
      setDryRunPassed(true);
      setCountdown(10);
      setRestartResult(null);
    } catch (error) {
      setMessage({ type: "error", text: error.message });
      setDryRunPassed(false);
      setCountdown(0);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRestart = async () => {
    if (!canExecuteRestart) {
      return;
    }
    const reason = form.reason.trim();
    const confirmText = form.confirm_text.trim();
    setIsRestarting(true);
    setMessage({ type: "", text: "" });
    setRestartResult(null);
    try {
      const result = await onRestart({
        admin_password: form.admin_password,
        reason,
        confirm_text: confirmText,
      });
      const portOk = Boolean(result?.db_port_reachable);
      setRestartResult(result);
      setMessage({
        type: portOk ? "success" : "error",
        text: portOk
          ? "MariaDB 재시작이 완료되었습니다. 3306 포트 응답을 확인했습니다."
          : "MariaDB 재시작 명령은 실행되었지만 3306 포트 응답 확인에 실패했습니다. 수동 점검이 필요합니다.",
      });
      setForm(INITIAL_FORM);
      setDryRunPassed(false);
      setCountdown(0);
      if (onRefreshStatus) {
        await onRefreshStatus();
      }
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setIsRestarting(false);
    }
  };

  const progressSteps = getProgressSteps({
    dryRunPassed,
    countdown,
    isRestarting,
    restartResult,
    hasError: message.type === "error",
  });

  return (
    <section className="scm-mariadb-panel" aria-labelledby="scm-mariadb-title">
      <div className="scm-mariadb-heading">
        <div>
          <span className="section-kicker">MariaDB Recovery</span>
          <h3 id="scm-mariadb-title">MariaDB 재시작 조건 확인</h3>
          <p>조건 확인 후 안전 대기 시간을 거쳐 MariaDB 서비스만 재시작합니다.</p>
        </div>
        <span className={restartEnabled ? "scm-live-badge" : "scm-dry-run-badge"}>
          {restartEnabled ? "실행 가능" : "기본 차단"}
        </span>
      </div>

      <div className={restartEnabled ? "scm-warning-box" : "scm-disabled-box"}>
        <strong>실행 범위 안내</strong>
        <span>{restartEnabled ? FINAL_WARNING : DISABLED_MESSAGE}</span>
      </div>

      <div className="scm-diagnosis-box">
        <strong>조건 확인 기준</strong>
        <ul>
          <li>Ping 또는 SSH는 정상인데 SCM 접속이 멈춘 경우</li>
          <li>MariaDB 상태가 inactive 또는 failed인 경우</li>
          <li>3306 포트가 응답하지 않아 DB freeze가 의심되는 경우</li>
        </ul>
      </div>

      <form className="scm-mariadb-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>재시작 사유</span>
          <textarea
            name="reason"
            rows="3"
            value={form.reason}
            onChange={handleChange}
            placeholder="예: 3306 포트 응답 없음, MariaDB freeze 의심"
          />
        </label>
        <label className="field">
          <span>관리자 비밀번호 재확인</span>
          <input
            type="password"
            name="admin_password"
            value={form.admin_password}
            onChange={handleChange}
            autoComplete="current-password"
            placeholder="관리자 비밀번호"
          />
        </label>
        <label className="field">
          <span>확인 문구 입력: MARIADB</span>
          <input
            type="text"
            name="confirm_text"
            value={form.confirm_text}
            onChange={handleChange}
            placeholder="MARIADB"
          />
        </label>

        {message.text ? (
          <div className={message.type === "success" ? "inline-success" : "inline-alert"}>
            {message.text}
          </div>
        ) : null}

        <div className="scm-restart-progress" aria-label="MariaDB 재시작 진행 상태">
          {progressSteps.map((step) => (
            <div className={`scm-restart-step scm-restart-step-${step.state}`} key={step.label}>
              <span>{step.label}</span>
              <strong>{step.text}</strong>
            </div>
          ))}
        </div>

        {dryRunPassed ? (
          <div className="scm-countdown-box">
            <span>최종 실행 대기</span>
            <strong>{countdown > 0 ? `${countdown}초` : "실행 가능"}</strong>
            <small>{FINAL_WARNING}</small>
          </div>
        ) : null}

        <div className="scm-mariadb-actions">
          <button type="submit" className="caution-button scm-dry-run-button" disabled={isSubmitting || isRestarting}>
            {isSubmitting ? "확인 중" : "MariaDB 재시작 조건 확인"}
          </button>
          <button
            type="button"
            className="danger-button scm-restart-execute-button"
            onClick={handleRestart}
            disabled={!canExecuteRestart}
          >
            {isRestarting ? "재시작 실행 중" : "MariaDB 재시작 실행"}
          </button>
          <span>
            {restartEnabled
              ? "조건 확인 성공 후 10초 대기가 끝나야 실제 실행할 수 있습니다."
              : "실제 실행은 설정이 활성화된 경우에만 가능합니다."}
          </span>
        </div>
      </form>
    </section>
  );
}

function getProgressSteps({ dryRunPassed, countdown, isRestarting, restartResult, hasError }) {
  const executed = Boolean(restartResult);
  const waitingDone = dryRunPassed && countdown === 0;
  return [
    {
      label: "관리자 인증 확인",
      text: dryRunPassed || isRestarting || executed ? "완료" : "대기",
      state: dryRunPassed || isRestarting || executed ? "done" : "pending",
    },
    {
      label: "MariaDB 현재 상태 확인",
      text: isRestarting || executed ? "진행" : "대기",
      state: isRestarting || executed ? "done" : "pending",
    },
    {
      label: "재시작 명령 전송",
      text: isRestarting ? "진행 중" : executed ? "완료" : waitingDone ? "대기" : "잠김",
      state: isRestarting ? "active" : executed ? "done" : "pending",
    },
    {
      label: "MariaDB 재기동 확인",
      text: executed ? formatRestartStatus(restartResult?.after_status) : isRestarting ? "확인 중" : "대기",
      state: executed ? "done" : isRestarting ? "active" : "pending",
    },
    {
      label: "3306 포트 확인",
      text: executed ? (restartResult?.db_port_reachable ? "응답 확인" : "확인 실패") : hasError ? "실패" : "대기",
      state: executed ? (restartResult?.db_port_reachable ? "done" : "error") : hasError ? "error" : "pending",
    },
  ];
}

function formatRestartStatus(status) {
  if (status === "active") {
    return "active";
  }
  if (status) {
    return String(status);
  }
  return "확인 중";
}

export default ScmMariaDbPanel;
