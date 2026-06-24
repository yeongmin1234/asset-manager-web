import React, { useEffect, useMemo, useState } from "react";

const FINAL_MESSAGE = "재부팅 조건 확인이 완료되었습니다. 현재 단계에서는 실제 reboot 명령을 실행하지 않습니다.";

const DRY_RUN_STEPS = [
  {
    id: "input-check",
    label: "입력값 확인",
    successMessage: "재부팅 사유와 필수 입력값이 확인되었습니다.",
  },
  {
    id: "admin-auth",
    label: "관리자 인증 확인",
    successMessage: "관리자 비밀번호 재확인이 완료되었습니다.",
  },
  {
    id: "confirm-text",
    label: "REBOOT 확인 문구 확인",
    successMessage: "확인 문구가 정확히 입력되었습니다.",
  },
  {
    id: "ssh-check",
    label: "SCM 서버 연결 확인",
    successMessage: "dry-run 단계에서는 연결 실행 없이 상태 확인 구조만 표시합니다.",
  },
  {
    id: "command-ready",
    label: "재부팅 명령 전송 준비",
    successMessage: "명령 전송 전 조건 확인까지만 완료되었습니다.",
  },
  {
    id: "shutdown-wait",
    label: "서버 종료 감지 대기",
    skippedMessage: "실제 재부팅 단계에서 진행합니다.",
  },
  {
    id: "boot-wait",
    label: "서버 재기동 대기",
    skippedMessage: "실제 재부팅 단계에서 진행합니다.",
  },
  {
    id: "recovery-check",
    label: "연결 복구 확인",
    skippedMessage: "실제 재부팅 단계에서 진행합니다.",
  },
  {
    id: "complete",
    label: "완료",
    successMessage: "dry-run 완료",
  },
];

function ScmRebootProgressModal({
  isOpen,
  isRefreshingStatus = false,
  onClose,
  onRefreshStatus,
  runKey = 0,
}) {
  const initialSteps = useMemo(() => buildInitialSteps(), []);
  const [steps, setSteps] = useState(initialSteps);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    setSteps(buildInitialSteps());
    setActiveIndex(0);
    setIsComplete(false);

    let stepIndex = 0;
    const timerIds = [];

    const advance = () => {
      setActiveIndex(stepIndex);
      setSteps((currentSteps) =>
        currentSteps.map((step, index) => {
          if (index < stepIndex) {
            return finalizeStep(step);
          }
          if (index === stepIndex) {
            return { ...step, status: "running", message: "확인 중입니다." };
          }
          return step;
        }),
      );

      const timerId = window.setTimeout(() => {
        setSteps((currentSteps) =>
          currentSteps.map((step, index) => (index === stepIndex ? finalizeStep(step) : step)),
        );

        if (stepIndex >= DRY_RUN_STEPS.length - 1) {
          setActiveIndex(-1);
          setIsComplete(true);
          return;
        }

        stepIndex += 1;
        advance();
      }, stepIndex < 5 ? 650 : 450);

      timerIds.push(timerId);
    };

    advance();

    return () => {
      timerIds.forEach((timerId) => window.clearTimeout(timerId));
    };
  }, [isOpen, runKey]);

  if (!isOpen) {
    return null;
  }

  const completedCount = steps.filter((step) => step.status === "success" || step.status === "skipped").length;

  return (
    <div className="scm-progress-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="scm-progress-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="scm-progress-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="scm-progress-heading">
          <div>
            <span className="section-kicker">Dry-run Progress</span>
            <h3 id="scm-progress-title">SCM 서버 재부팅 진행상황</h3>
            <p>현재 단계에서는 dry-run이며 실제 reboot 명령은 실행되지 않습니다.</p>
          </div>
          <span className="scm-progress-mode-badge">Dry-run 전용</span>
        </div>

        <div className="scm-progress-summary">
          <span>{completedCount} / {steps.length}</span>
          <strong>{isComplete ? "조건 확인 완료" : "단계 확인 중"}</strong>
          <p>{isComplete ? FINAL_MESSAGE : "입력값과 안전 조건을 순차적으로 확인하는 UI입니다."}</p>
        </div>

        <ol className="scm-progress-step-list">
          {steps.map((step, index) => (
            <li className={`scm-progress-step scm-progress-step-${step.status}`} key={step.id}>
              <span className="scm-progress-step-marker" aria-hidden="true">
                {getStepSymbol(step.status, index === activeIndex)}
              </span>
              <div>
                <strong>{step.label}</strong>
                <p>{step.message}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="scm-progress-note">
          3단계 실제 재부팅 기능에서는 이 단계 상태를 polling API와 연결할 예정입니다.
        </div>

        <div className="scm-progress-actions">
          <button type="button" className="secondary-button" onClick={onRefreshStatus} disabled={isRefreshingStatus}>
            {isRefreshingStatus ? "확인 중" : "상태 새로고침"}
          </button>
          <button type="button" className="secondary-button" onClick={onClose}>
            닫기
          </button>
        </div>
      </section>
    </div>
  );
}

function buildInitialSteps() {
  return DRY_RUN_STEPS.map((step, index) => ({
    ...step,
    status: index === 0 ? "pending" : "pending",
    message: index < 5 ? "확인 대기" : index < 8 ? "실제 재부팅 단계에서 진행" : "dry-run 완료 대기",
  }));
}

function finalizeStep(step) {
  if (step.id === "shutdown-wait" || step.id === "boot-wait" || step.id === "recovery-check") {
    return {
      ...step,
      status: "skipped",
      message: step.skippedMessage || "실제 재부팅 단계에서 진행합니다.",
    };
  }
  return {
    ...step,
    status: "success",
    message: step.successMessage || "확인 완료",
  };
}

function getStepSymbol(status, isActive) {
  if (status === "success") {
    return "✓";
  }
  if (status === "skipped") {
    return "—";
  }
  if (status === "failed") {
    return "!";
  }
  if (status === "warning") {
    return "!";
  }
  return isActive || status === "running" ? "…" : "";
}

export default ScmRebootProgressModal;
