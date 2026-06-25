import React, { useState } from "react";

const SUCCESS_MESSAGE = "MariaDB 재시작 조건 확인이 완료되었습니다. 현재 단계에서는 실제 재시작 명령을 실행하지 않습니다.";

const INITIAL_FORM = {
  admin_password: "",
  reason: "",
  confirm_text: "",
};

function ScmMariaDbPanel({ onDryRun }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      setForm((current) => ({ ...current, admin_password: "", confirm_text: "" }));
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="scm-mariadb-panel" aria-labelledby="scm-mariadb-title">
      <div className="scm-mariadb-heading">
        <div>
          <span className="section-kicker">MariaDB Recovery</span>
          <h3 id="scm-mariadb-title">MariaDB 재시작 조건 확인</h3>
          <p>Ping/SSH와 3306 포트 상태를 바탕으로 재시작 검토 조건만 확인합니다.</p>
        </div>
        <span className="scm-dry-run-badge">Dry-run 전용</span>
      </div>

      <div className="scm-warning-box">
        <strong>실행 범위 안내</strong>
        <span>현재 단계에서는 조건 확인만 수행하며 실제 MariaDB 재시작 명령은 실행하지 않습니다.</span>
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

        <div className="scm-mariadb-actions">
          <button type="submit" className="caution-button scm-dry-run-button" disabled={isSubmitting}>
            {isSubmitting ? "확인 중" : "MariaDB 재시작 조건 확인"}
          </button>
          <span>확인 문구는 MARIADB이며, dry-run API만 호출합니다.</span>
        </div>
      </form>
    </section>
  );
}

export default ScmMariaDbPanel;
