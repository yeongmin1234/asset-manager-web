import React, { useEffect, useState } from "react";

const INITIAL_FORM = {
  admin_password: "",
  reason: "",
  confirm_text: "",
};

function ScmRebootDryRunPanel({ onDryRun, onDryRunSuccess }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [countdown, setCountdown] = useState(10);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (countdown <= 0) {
      return undefined;
    }
    const timerId = window.setTimeout(() => setCountdown((current) => current - 1), 1000);
    return () => window.clearTimeout(timerId);
  }, [countdown]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setMessage({ type: "", text: "" });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const reason = form.reason.trim();
    const confirmText = form.confirm_text.trim();
    if (!reason) {
      setMessage({ type: "error", text: "재부팅 사유를 입력해주세요." });
      return;
    }
    if (confirmText !== "REBOOT") {
      setMessage({ type: "error", text: "확인 문구를 정확히 REBOOT로 입력해주세요." });
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
        text: result?.message || "재부팅 실행 조건 확인이 완료되었습니다. 현재 단계에서는 실제 재부팅을 실행하지 않습니다.",
      });
      setForm((current) => ({ ...current, admin_password: "", confirm_text: "" }));
      setCountdown(10);
      onDryRunSuccess?.(result);
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="scm-reboot-panel" aria-labelledby="scm-reboot-title">
      <div className="scm-reboot-heading">
        <div>
          <span className="section-kicker">Dry-run Only</span>
          <h3 id="scm-reboot-title">재부팅 준비</h3>
          <p>이번 단계에서는 조건 확인만 수행하며 실제 재부팅 명령은 실행하지 않습니다.</p>
        </div>
        <span className="scm-dry-run-badge">Dry-run 전용</span>
      </div>

      <div className="scm-warning-box">
        <strong>주의</strong>
        <span>SCM 서버를 재부팅하면 업무 중 접속이 일시적으로 중단될 수 있습니다.</span>
      </div>

      <div className="scm-countdown-box">
        <span>재부팅 실행 전 안전 대기 UI</span>
        <strong>{countdown > 0 ? `${countdown}초` : "대기 종료"}</strong>
        <small>카운트다운이 끝나도 실제 reboot 명령은 실행되지 않습니다.</small>
      </div>

      <form className="scm-reboot-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>재부팅 사유</span>
          <textarea
            name="reason"
            rows="3"
            value={form.reason}
            onChange={handleChange}
            placeholder="예: 정기 점검 전 재부팅 준비 확인"
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
          <span>확인 문구 입력: REBOOT</span>
          <input
            type="text"
            name="confirm_text"
            value={form.confirm_text}
            onChange={handleChange}
            placeholder="REBOOT"
          />
        </label>

        {message.text ? (
          <div className={message.type === "success" ? "inline-success" : "inline-alert"}>
            {message.text}
          </div>
        ) : null}

        <div className="scm-reboot-actions">
          <button type="submit" className="caution-button scm-dry-run-button" disabled={isSubmitting}>
            {isSubmitting ? "확인 중" : "재부팅 조건 확인"}
          </button>
          <span>dry-run API만 호출하며 실제 reboot 명령은 실행하지 않습니다.</span>
        </div>
      </form>
    </section>
  );
}

export default ScmRebootDryRunPanel;
