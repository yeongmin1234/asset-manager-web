import React from "react";

const MASKED_PASSWORD = "••••••••";

function NetworkCredentialList({
  credentials = [],
  error = "",
  isLoading = false,
  revealedPasswords = {},
  onCopyPassword,
  onDelete,
  onEdit,
  onRevealPassword,
}) {
  if (error) {
    return <div className="empty-state error-state">접속정보를 불러오지 못했습니다. {error}</div>;
  }

  if (isLoading && credentials.length === 0) {
    return <div className="empty-state">접속정보를 불러오는 중입니다.</div>;
  }

  if (!isLoading && credentials.length === 0) {
    return <div className="empty-state">등록된 접속정보가 없습니다.</div>;
  }

  return (
    <div className="table-scroll network-credential-table-scroll">
      <table className="data-table network-credential-table">
        <thead>
          <tr>
            <th>구분</th>
            <th>서비스명</th>
            <th>내부 주소</th>
            <th>외부 주소</th>
            <th>계정</th>
            <th>중요도</th>
            <th>비밀번호</th>
            <th>비고</th>
            <th>관리</th>
          </tr>
        </thead>
        <tbody>
          {credentials.map((credential) => {
            const revealed = revealedPasswords[credential.id];
            return (
              <tr key={credential.id}>
                <td>{displayValue(credential.category)}</td>
                <td>
                  <strong className="network-credential-service">
                    {displayValue(credential.service_name)}
                  </strong>
                  {credential.port ? <small>:{credential.port}</small> : null}
                </td>
                <td>{renderUrl(credential.internal_url)}</td>
                <td>{renderUrl(credential.external_url)}</td>
                <td>{displayValue(credential.username)}</td>
                <td>
                  <span className={`importance-badge ${getImportanceClass(credential.importance)}`}>
                    {displayValue(credential.importance)}
                  </span>
                </td>
                <td>
                  {credential.has_password ? (
                    <div className="network-password-cell">
                      <button
                        type="button"
                        className={revealed ? "network-password-value" : "network-password-mask"}
                        onClick={() =>
                          revealed
                            ? onCopyPassword?.(credential, "copy-visible")
                            : onRevealPassword?.(credential)
                        }
                        title={revealed ? "클릭하여 복사" : "비밀번호 보기"}
                      >
                        {revealed || MASKED_PASSWORD}
                      </button>
                      <div className="network-password-actions">
                        <button type="button" className="secondary-button compact-button" onClick={() => onRevealPassword?.(credential)}>
                          보기
                        </button>
                        <button type="button" className="secondary-button compact-button" onClick={() => onCopyPassword?.(credential)}>
                          복사
                        </button>
                      </div>
                    </div>
                  ) : (
                    <span className="muted-text">없음</span>
                  )}
                </td>
                <td className="network-credential-note" title={credential.note || ""}>
                  {displayValue(credential.note)}
                </td>
                <td>
                  <div className="network-credential-actions">
                    <button type="button" className="secondary-button compact-button" onClick={() => onEdit?.(credential)}>
                      수정
                    </button>
                    <button type="button" className="danger-button compact-button" onClick={() => onDelete?.(credential)}>
                      삭제
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function renderUrl(value) {
  if (!value) {
    return "-";
  }
  const href = toHref(value);
  return (
    <a className="network-credential-url" href={href} target="_blank" rel="noreferrer" title={value}>
      {value}
    </a>
  );
}

function toHref(value) {
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  return `http://${value}`;
}

function getImportanceClass(importance) {
  if (importance === "매우중요") {
    return "importance-critical";
  }
  if (importance === "중요") {
    return "importance-important";
  }
  return "importance-normal";
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

export default NetworkCredentialList;
