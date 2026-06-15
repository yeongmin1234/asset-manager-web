import React, { useMemo, useState } from "react";
import StatusBadge from "./StatusBadge.jsx";

const CATEGORY_EXAMPLES = ["노트북", "모니터", "프린터", "네트워크 장비", "기타"];
const REQUIRED_EXCEL_COLUMNS = ["제품명", "분류", "상태"];
const OPTIONAL_EXCEL_COLUMNS = ["시리얼번호", "부서(사용자명)", "구매일", "메모"];
const LIST_COLUMNS = ["제품명", "상태", "시리얼번호", "부서(사용자명)", "구매일"];

const SETTINGS_SECTIONS = [
  {
    id: "basic",
    label: "기본 정보",
    description: "회사명, 시스템명, 운영 환경",
    icon: "i",
  },
  {
    id: "master",
    label: "자산 기준",
    description: "분류, 상태값, 부서 기준",
    icon: "M",
  },
  {
    id: "excel",
    label: "엑셀 설정",
    description: "업로드 양식과 검증 규칙",
    icon: "X",
  },
  {
    id: "display",
    label: "화면 설정",
    description: "목록 표시, 기본 화면 기준",
    icon: "D",
  },
  {
    id: "backup",
    label: "데이터/백업",
    description: "백업 정책과 데이터 관리 안내",
    icon: "B",
  },
  {
    id: "system",
    label: "시스템 정보",
    description: "Frontend, Backend, DB 상태",
    icon: "S",
  },
];

const formatBackendStatus = (backendStatus) => {
  if (backendStatus?.loading) return "상태 확인 중";
  if (backendStatus?.ok) return "Backend 정상 / DB 정상";
  if (backendStatus?.status === "idle") return "상태 확인 대기";
  return "연결 확인 필요";
};

function SettingsCard({ title, description, children, action }) {
  return (
    <section className="settings-card">
      <div className="settings-card-heading">
        <div>
          <h4>{title}</h4>
          {description ? <p>{description}</p> : null}
        </div>
        {action ? <div className="settings-card-action">{action}</div> : null}
      </div>
      <div className="settings-card-body">{children}</div>
    </section>
  );
}

function InfoList({ items }) {
  return (
    <dl className="settings-info-list">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function ColumnGroup({ title, columns, tone = "blue" }) {
  return (
    <div className="settings-column-group">
      <strong>{title}</strong>
      <div className="settings-chip-list">
        {columns.map((column) => (
          <span className={`settings-chip settings-chip-${tone}`} key={column}>
            {column}
          </span>
        ))}
      </div>
    </div>
  );
}

function RuleList({ rules }) {
  return (
    <ul className="settings-rule-list">
      {rules.map((rule) => (
        <li key={rule}>{rule}</li>
      ))}
    </ul>
  );
}

function SettingsPage({ backendStatus, onCheckBackend, onNavigate }) {
  const [activeSettingsSection, setActiveSettingsSection] = useState("basic");

  const activeSection = useMemo(
    () =>
      SETTINGS_SECTIONS.find((section) => section.id === activeSettingsSection) ||
      SETTINGS_SECTIONS[0],
    [activeSettingsSection],
  );

  const statusText = formatBackendStatus(backendStatus);

  const renderDetail = () => {
    switch (activeSettingsSection) {
      case "master":
        return (
          <div className="settings-grid">
            <SettingsCard
              title="분류/부서 기준"
              description="현재 자산 등록과 엑셀 업로드에서 사용하는 기준입니다."
            >
              <ColumnGroup title="분류 예시" columns={CATEGORY_EXAMPLES} />
              <InfoList
                items={[
                  { label: "부서 입력", value: "부서(사용자명) 자유 입력" },
                  { label: "운영 방식", value: "현재는 기준 안내만 제공" },
                  { label: "향후 확장", value: "분류/부서 CRUD로 확장 가능" },
                ]}
              />
            </SettingsCard>
            <SettingsCard title="상태값 기준" description="자산 목록과 상세 화면에서 동일하게 표시합니다.">
              <div className="settings-status-list">
                <div className="settings-status-item">
                  <StatusBadge status="사용중" />
                  <span>현재 사용 중인 자산</span>
                </div>
                <div className="settings-status-item">
                  <StatusBadge status="미사용" />
                  <span>보관 중이거나 배정 전인 자산</span>
                </div>
                <div className="settings-status-item">
                  <StatusBadge status="폐기" />
                  <span>사용 종료 또는 폐기 처리된 자산</span>
                </div>
              </div>
            </SettingsCard>
          </div>
        );
      case "excel":
        return (
          <div className="settings-grid-single">
            <SettingsCard
              title="엑셀 업로드 기준"
              description="양식 다운로드, 미리보기, 정상 행 일괄 등록에 공통 적용되는 규칙입니다."
              action={
                <button className="btn btn-secondary" type="button" onClick={() => onNavigate?.("excel")}>
                  엑셀 관리로 이동
                </button>
              }
            >
              <div className="settings-two-column">
                <ColumnGroup title="필수 컬럼" columns={REQUIRED_EXCEL_COLUMNS} tone="blue" />
                <ColumnGroup title="선택 컬럼" columns={OPTIONAL_EXCEL_COLUMNS} tone="gray" />
              </div>
              <RuleList
                rules={[
                  "시리얼번호는 영문 대문자 A-Z와 숫자 0-9만 허용합니다.",
                  "중복 시리얼번호는 등록할 수 없습니다.",
                  "구매일은 YYYY-MM-DD 형식을 권장합니다.",
                  "오류 행은 저장하지 않고 정상 행만 일괄 등록합니다.",
                ]}
              />
            </SettingsCard>
          </div>
        );
      case "display":
        return (
          <div className="settings-grid-single">
            <SettingsCard title="화면 표시 기준" description="현재 포털 UI에 적용된 기본 표시 정책입니다.">
              <InfoList
                items={[
                  { label: "테마", value: "밝은 테마" },
                  { label: "레이아웃", value: "포털형 사이드바" },
                  { label: "주 사용 환경", value: "PC/노트북 중심" },
                  { label: "반응형", value: "모바일 1열 표시 지원" },
                  { label: "기본 정렬", value: "최근 등록순" },
                ]}
              />
              <ColumnGroup title="자산 목록 표시 컬럼" columns={LIST_COLUMNS} tone="blue" />
            </SettingsCard>
          </div>
        );
      case "backup":
        return (
          <div className="settings-grid">
            <SettingsCard title="데이터/백업 안내" description="운영 전 점검해야 할 데이터 관리 기준입니다.">
              <RuleList
                rules={[
                  "운영 DB는 정기 백업 정책을 별도로 수립해야 합니다.",
                  "배포 전에는 DB와 환경 파일 백업을 권장합니다.",
                  ".env 파일은 백업하되 Git에는 올리지 않습니다.",
                  "엑셀 내보내기는 데이터 확인 및 보조 백업 용도로 사용합니다.",
                ]}
              />
            </SettingsCard>
            <SettingsCard title="사용자/권한 안내" description="현재는 제한된 내부 사용을 전제로 합니다.">
              <ColumnGroup title="향후 권한 구조 예시" columns={["관리자", "일반 사용자", "조회 전용"]} />
              <p className="settings-muted">
                이번 단계에서는 실제 계정 생성, 로그인, 권한 부여 기능을 제공하지 않습니다.
              </p>
            </SettingsCard>
          </div>
        );
      case "system":
        return (
          <div className="settings-grid-single">
            <SettingsCard
              title="시스템 상태"
              description="현재 로컬 개발 기준의 상태와 접속 정보를 확인합니다."
              action={
                <button
                  className="btn btn-secondary"
                  type="button"
                  onClick={onCheckBackend}
                  disabled={backendStatus?.loading}
                >
                  {backendStatus?.loading ? "확인 중..." : "상태 확인"}
                </button>
              }
            >
              <InfoList
                items={[
                  { label: "Frontend", value: "http://127.0.0.1:5173" },
                  { label: "Backend", value: "http://127.0.0.1:8001" },
                  { label: "Backend/DB", value: statusText },
                  { label: "버전", value: "Local Preview Version" },
                ]}
              />
              <div className="settings-status-inline">
                <StatusBadge status={backendStatus?.ok ? "사용중" : "미사용"} />
                <span>{statusText}</span>
              </div>
            </SettingsCard>
          </div>
        );
      case "basic":
      default:
        return (
          <div className="settings-grid-single">
            <SettingsCard title="운영 정보" description="저장 기능 없이 현재 적용 기준을 확인하는 영역입니다.">
              <InfoList
                items={[
                  { label: "시스템명", value: "사내 자산관리 시스템" },
                  { label: "회사명", value: "The Limo &" },
                  { label: "관리 부서", value: "총무팀" },
                  { label: "운영 환경", value: "로컬 개발 환경 / NAS 배포 예정" },
                  { label: "로고", value: "사이드바 상단에 회사 로고 적용" },
                ]}
              />
              <p className="settings-muted">
                향후 저장 기능이 필요해질 경우 이 영역에 운영 정보 수정 기능을 연결할 수 있습니다.
              </p>
            </SettingsCard>
          </div>
        );
    }
  };

  return (
    <section className="settings-page" aria-labelledby="settings-title">
      <div className="settings-hero">
        <div>
          <span className="section-kicker">System Settings</span>
          <h2 id="settings-title">설정</h2>
          <p>시스템 운영 기준과 관리 정보를 확인합니다.</p>
        </div>
        <span className="settings-version-badge">Local Preview Version</span>
      </div>

      <div className="settings-layout">
        <aside className="settings-side-nav" aria-label="설정 목록">
          {SETTINGS_SECTIONS.map((section) => (
            <button
              className={`settings-nav-item ${activeSettingsSection === section.id ? "active" : ""}`}
              key={section.id}
              type="button"
              onClick={() => setActiveSettingsSection(section.id)}
            >
              <span className="settings-nav-icon" aria-hidden="true">
                {section.icon}
              </span>
              <span>
                <strong>{section.label}</strong>
                <small>{section.description}</small>
              </span>
            </button>
          ))}
        </aside>

        <div className="settings-detail-panel">
          <div className="settings-detail-heading">
            <div>
              <h3>{activeSection.label}</h3>
              <p>{activeSection.description}</p>
            </div>
          </div>
          <div className="settings-detail-content">{renderDetail()}</div>
        </div>
      </div>
    </section>
  );
}

export default SettingsPage;
