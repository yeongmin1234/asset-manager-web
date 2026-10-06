import React, { useEffect, useState } from "react";
import ProductManagement from "./ProductManagement";
import StaffManagement from "./StaffManagement";
import CustomerConsulting from "./CustomerConsulting";
import ConsultationList from "./ConsultationList";
import AsManagement from "./AsManagement";
import SalesManagement from "./SalesManagement";
import LogisticsManagement from "./LogisticsManagement";
import NoticeManagement from "./NoticeManagement";
import HomeBusinessDashboard from "./HomeDashboard";
import SettingsManagement from "./SettingsManagement";
import { CustomerManagementPage, MemoSearchPage, NotFoundPage, OrderSupportPage } from "./pages/WorkspacePages";
import { useAuth } from "./contexts/AuthContext";
import { PermissionState, StatusBadge } from "./components/common/CommonUI";
import ActiveUsersIndicator from "./components/layout/ActiveUsersIndicator";

const menus = [
  { label: "HOME", path: "/" },
  { label: "매장관리", path: "/store-management/staff" },
  { label: "고객상담", path: "/customer-consulting" },
  { label: "고객관리", path: "/customers" },
  { label: "상담목록", path: "/consultations" },
  { label: "A/S", path: "/as" },
  { label: "판매", path: "/sales" },
  { label: "물류", path: "/logistics" },
  { label: "대여제품관리", path: "/rentals", visible: false },
  { label: "통계", path: "/statistics", visible: false },
  { label: "발주지원센터", path: "/order-support" },
  { label: "공지사항", path: "/notices" },
  { label: "메모검색", path: "/memo-search" },
  { label: "환경설정", path: "/settings" },
  { label: "지출결의서", path: "/expenses", visible: false },
];

const hiddenMenuPaths = new Set([
  ...menus.filter((menu) => menu.visible === false).map((menu) => menu.path),
  "/expense-resolution",
]);

const storeSubmenus = [
  { label: "직원리스트", path: "/store-management/staff" },
  { label: "상품등록", path: "/store-management/products" },
  { label: "매장리스트", path: "/store-management/stores" },
  { label: "통계", path: "/store-management/statistics" },
  { label: "공지사항", path: "/store-management/notices" },
];

const storeSalesData = [];

const summaryCards = [];

const recentOrders = [];

const notifications = [];

const recentActivities = [];

function getCurrentPath() {
  const path = window.location.hash.slice(1).replace(/\/+$/, "") || "/";

  if (hiddenMenuPaths.has(path)) {
    window.history.replaceState({}, "", "#/");
    return "/";
  }

  return path;
}

function LegacyHomeDashboard() {
  return (
    <section className="dashboard" aria-labelledby="page-title">
      <div className="dashboard__heading">
        <div>
          <p className="dashboard__eyebrow">SCM DASHBOARD</p>
          <h1 id="page-title">HOME</h1>
          <p>주요 업무 현황을 한눈에 확인합니다.</p>
        </div>
        <span className="page-panel__status">프론트엔드 개발 모드</span>
      </div>

      <div className="summary-grid">
        {summaryCards.map((card) => (
          <article className="summary-card" key={card.label}>
            <p>{card.label}</p>
            <strong>{card.value}</strong>
            <span>{card.note}</span>
          </article>
        ))}
      </div>

      <div className="dashboard__columns">
        <section className="data-panel" aria-labelledby="recent-orders-title">
          <div className="data-panel__header">
            <h2 id="recent-orders-title">최근 주문 현황</h2>
            <span>최근 4건</span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>주문번호</th>
                  <th>거래처</th>
                  <th>상품명</th>
                  <th>수량</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.map((order) => (
                  <tr key={order.number}>
                    <td className="table-key">{order.number}</td>
                    <td>{order.partner}</td>
                    <td>{order.product}</td>
                    <td>{order.quantity}</td>
                    <td><StatusBadge status={order.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="data-panel" aria-labelledby="notifications-title">
          <div className="data-panel__header">
            <h2 id="notifications-title">업무 알림</h2>
            <span>4개 항목</span>
          </div>
          <ul className="notification-list">
            {notifications.map((notification) => (
              <li key={notification.type}>
                <StatusBadge status={notification.type} />
                <p>{notification.detail}</p>
                <button type="button" aria-label={`${notification.type} 항목 확인`}>
                  확인
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="data-panel" aria-labelledby="recent-activities-title">
        <div className="data-panel__header">
          <h2 id="recent-activities-title">최근 작업 내역</h2>
          <span>고정 임시 데이터</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>일시</th>
                <th>메뉴</th>
                <th>작업 내용</th>
                <th>담당자</th>
                <th>상태</th>
              </tr>
            </thead>
            <tbody>
              {recentActivities.map((activity) => (
                <tr key={`${activity.date}-${activity.detail}`}>
                  <td>{activity.date}</td>
                  <td>{activity.menu}</td>
                  <td className="table-key">{activity.detail}</td>
                  <td>{activity.manager}</td>
                  <td><StatusBadge status={activity.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

function StoreTable({ columns, rows }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${row[0]}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${cell}-${cellIndex}`}>
                  {cellIndex === row.length - 1 ? (
                    <StatusBadge status={cell} />
                  ) : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatMetric(value, basis) {
  return basis === "quantity"
    ? `${Math.round(value).toLocaleString("ko-KR")}개`
    : `${Math.round(value).toLocaleString("ko-KR")}원`;
}

function getComparisonData(side, year, month, basis) {
  const monthBase = side === "left" ? "june" : "july";
  const monthAdjustment = 1 + (Number(month) - (side === "left" ? 6 : 7)) * 0.018;
  const yearAdjustment = 1 + (Number(year) - 2026) * 0.035;
  const basisAdjustment = basis === "supply" ? 0.72 : 1;

  return storeSalesData.map((store, index) => {
    const baseValue =
      basis === "quantity"
        ? store.quantity * (side === "right" ? 1.06 : 1)
        : store[monthBase];
    const variation = 1 + ((index % 4) - 1.5) * 0.006;

    return {
      name: store.name,
      value: Math.max(0, baseValue * monthAdjustment * yearAdjustment * basisAdjustment * variation),
    };
  });
}

function SalesBarChart({ data, basis, showValues, label }) {
  const maxValue = Math.max(...data.map((item) => item.value), 1);
  const tickValues = [0, 0.25, 0.5, 0.75, 1].map((ratio) => maxValue * ratio);

  return (
    <section className="sales-chart-panel" aria-label={`${label} 매장별 실적`}>
      <div className="sales-chart-panel__title">
        <h3>{label}</h3>
        <span>{data.length}개 매장</span>
      </div>
      <div className="sales-axis" aria-hidden="true">
        {tickValues.map((tick) => (
          <span key={tick}>{formatMetric(tick, basis)}</span>
        ))}
      </div>
      <div className="sales-bars">
        {data.map((item, index) => (
          <div className="sales-bar-row" key={item.name}>
            <span className="sales-bar-row__name">{item.name}</span>
            <div className="sales-bar-row__track">
              <span
                className={`sales-bar-row__fill sales-bar-row__fill--${(index % 5) + 1}`}
                style={{ width: `${item.value === 0 ? 0 : Math.max(2, (item.value / maxValue) * 100)}%` }}
                title={`${item.name}: ${formatMetric(item.value, basis)}`}
                data-tooltip={`${item.name} · ${formatMetric(item.value, basis)}`}
              />
            </div>
            {showValues && <strong>{formatMetric(item.value, basis)}</strong>}
          </div>
        ))}
      </div>
    </section>
  );
}

function StoreSalesStatistics() {
  const [leftCondition, setLeftCondition] = useState({ year: "2026", month: "6", basis: "sale" });
  const [rightCondition, setRightCondition] = useState({ year: "2026", month: "7", basis: "sale" });
  const [sortBy, setSortBy] = useState("high");
  const [showValues, setShowValues] = useState(true);
  const [hideZero, setHideZero] = useState(false);
  const [viewLimit, setViewLimit] = useState("all");

  const basis = leftCondition.basis;
  const basisLabels = { sale: "판매가", supply: "공급가", quantity: "수량" };

  function prepareData(data) {
    let result = hideZero ? data.filter((item) => item.value > 0) : [...data];

    if (viewLimit === "top10") {
      result = [...result].sort((a, b) => b.value - a.value).slice(0, 10);
    }

    result.sort((a, b) => {
      if (sortBy === "low") return a.value - b.value;
      if (sortBy === "name") return a.name.localeCompare(b.name, "ko");
      return b.value - a.value;
    });

    return result;
  }

  const leftData = prepareData(
    getComparisonData("left", leftCondition.year, leftCondition.month, leftCondition.basis),
  );
  const rightData = prepareData(
    getComparisonData("right", rightCondition.year, rightCondition.month, rightCondition.basis),
  );
  const leftTotal = leftData.reduce((sum, item) => sum + item.value, 0);
  const rightTotal = rightData.reduce((sum, item) => sum + item.value, 0);
  const difference = rightTotal - leftTotal;
  const changeRate = leftTotal === 0 ? 0 : (difference / leftTotal) * 100;
  const changeTone = difference > 0 ? "increase" : difference < 0 ? "decrease" : "same";

  function updateCondition(side, key, value) {
    const setter = side === "left" ? setLeftCondition : setRightCondition;
    setter((current) => ({ ...current, [key]: value }));

    if (key === "basis") {
      const otherSetter = side === "left" ? setRightCondition : setLeftCondition;
      otherSetter((current) => ({ ...current, basis: value }));
    }
  }

  function ConditionBox({ side, condition, title }) {
    return (
      <fieldset className="comparison-condition">
        <legend>{title}</legend>
        <label>
          <span>연도</span>
          <select value={condition.year} onChange={(event) => updateCondition(side, "year", event.target.value)}>
            {["2024", "2025", "2026"].map((year) => <option key={year} value={year}>{year}년</option>)}
          </select>
        </label>
        <label>
          <span>월</span>
          <select value={condition.month} onChange={(event) => updateCondition(side, "month", event.target.value)}>
            {Array.from({ length: 12 }, (_, index) => String(index + 1)).map((month) => (
              <option key={month} value={month}>{month}월</option>
            ))}
          </select>
        </label>
        <label>
          <span>기준</span>
          <select value={condition.basis} onChange={(event) => updateCondition(side, "basis", event.target.value)}>
            <option value="sale">판매가</option>
            <option value="supply">공급가</option>
            <option value="quantity">수량</option>
          </select>
        </label>
      </fieldset>
    );
  }

  return (
    <section className="store-content store-content--statistics" aria-labelledby="store-content-title">
      <div className="statistics-title">
        <p>MONTHLY SALES COMPARISON</p>
        <h2 id="store-content-title">매장별 매출 통계</h2>
      </div>

      <div className="comparison-conditions">
        <ConditionBox side="left" condition={leftCondition} title="첫 번째 비교 조건" />
        <ConditionBox side="right" condition={rightCondition} title="두 번째 비교 조건" />
      </div>

      <div className="sales-summary">
        <article><span>왼쪽 월 총매출</span><strong>{formatMetric(leftTotal, basis)}</strong></article>
        <article><span>오른쪽 월 총매출</span><strong>{formatMetric(rightTotal, basis)}</strong></article>
        <article className={`sales-summary--${changeTone}`}>
          <span>증감액</span><strong>{difference > 0 ? "+" : ""}{formatMetric(difference, basis)}</strong>
        </article>
        <article className={`sales-summary--${changeTone}`}>
          <span>증감률</span><strong>{changeRate > 0 ? "+" : ""}{changeRate.toFixed(1)}%</strong>
        </article>
      </div>

      <div className="chart-options">
        <label>
          <span>정렬</span>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
            <option value="high">매출 높은 순</option>
            <option value="low">매출 낮은 순</option>
            <option value="name">매장명 순</option>
          </select>
        </label>
        <label className="check-option">
          <input type="checkbox" checked={showValues} onChange={(event) => setShowValues(event.target.checked)} />
          금액 표시
        </label>
        <label className="check-option">
          <input type="checkbox" checked={hideZero} onChange={(event) => setHideZero(event.target.checked)} />
          0원 매장 숨기기
        </label>
        <div className="view-toggle" aria-label="표시 매장 수">
          <button type="button" className={viewLimit === "top10" ? "active" : ""} onClick={() => setViewLimit("top10")}>상위 10개</button>
          <button type="button" className={viewLimit === "all" ? "active" : ""} onClick={() => setViewLimit("all")}>전체 보기</button>
        </div>
      </div>

      <div className="comparison-charts">
        <SalesBarChart
          data={leftData}
          basis={leftCondition.basis}
          showValues={showValues}
          label={`${leftCondition.year}년 ${leftCondition.month}월 · ${basisLabels[leftCondition.basis]}`}
        />
        <SalesBarChart
          data={rightData}
          basis={rightCondition.basis}
          showValues={showValues}
          label={`${rightCondition.year}년 ${rightCondition.month}월 · ${basisLabels[rightCondition.basis]}`}
        />
      </div>
    </section>
  );
}

function StoreSubContent({ currentPath }) {
  if (currentPath === "/store-management/products") {
    return <ProductManagement />;
  }

  if (currentPath === "/store-management/stores") {
    return (
      <section className="store-content" aria-labelledby="store-content-title">
        <div className="store-content__header">
          <h2 id="store-content-title">매장리스트</h2>
          <p>등록된 매장의 기본 현황입니다.</p>
        </div>
        <StoreTable
          columns={["매장코드", "매장명", "지역", "담당자", "연락처", "상태"]}
          rows={[]}
        />
      </section>
    );
  }

  if (currentPath === "/store-management/statistics") {
    return <StoreSalesStatistics />;
  }

  if (currentPath === "/store-management/notices") {
    return (
      <section className="store-content" aria-labelledby="store-content-title">
        <div className="store-content__header">
          <h2 id="store-content-title">공지사항</h2>
          <p>매장 운영 관련 공지 목록입니다.</p>
        </div>
        <StoreTable
          columns={["번호", "등록일", "제목", "작성자", "읽음 여부"]}
          rows={[]}
        />
      </section>
    );
  }

  return (
    <StaffManagement />
  );
}

function StoreManagement({ currentPath, onNavigate }) {
  const selectedSubmenu =
    storeSubmenus.find((submenu) => submenu.path === currentPath) ?? storeSubmenus[0];

  return (
    <section className="store-page" aria-labelledby="page-title">
      <div className="store-page__heading">
        <div>
          <p>STORE MANAGEMENT</p>
          <h1 id="page-title">매장관리</h1>
        </div>
        <span className="page-panel__status">프론트엔드 개발 모드</span>
      </div>
      <div className="store-layout">
        <aside className="store-sidebar" aria-label="매장관리 하위 메뉴">
          <p>매장관리</p>
          <nav>
            {storeSubmenus.map((submenu) => {
              const isActive = submenu.path === selectedSubmenu.path;
              return (
                <a
                  key={submenu.path}
                  href={`#${submenu.path}`}
                  className={isActive ? "store-sidebar__active" : ""}
                  aria-current={isActive ? "page" : undefined}
                  onClick={(event) => onNavigate(event, submenu.path)}
                >
                  {submenu.label}
                </a>
              );
            })}
          </nav>
        </aside>
        <StoreSubContent currentPath={selectedSubmenu.path} />
      </div>
    </section>
  );
}

function App() {
  const [currentPath, setCurrentPath] = useState(getCurrentPath);
  const { currentUser, canAccess, isDevMode } = useAuth();
  const customerConsultingPaths = new Set(["/customer-consulting","/customer-consulting/as-reception","/customer-consulting/sales-reception","/customer-consulting/consultation-list","/customer-consulting/return-list","/customer-consulting/exchange-list","/customer-consulting/as-list","/customer-consulting/sales-list","/customer-consulting/logistics-list","/customer-consulting/logistics-management"]);
  const settingsPaths = new Set(["/settings","/settings/accounts","/settings/codes","/settings/batches","/settings/markets","/settings/data-mapping","/settings/as","/settings/symptoms","/settings/filter-sms","/settings/send-status","/settings/opt-out","/settings/target-products","/settings/bmdmall","/settings/serial-update"]);
  const isStoreManagement = storeSubmenus.some((submenu) => submenu.path === currentPath);
  const isCustomerConsulting = customerConsultingPaths.has(currentPath);
  const isSettings = settingsPaths.has(currentPath);
  const currentMenu =
    (isStoreManagement
      ? menus.find((menu) => menu.label === "매장관리")
      : isCustomerConsulting
        ? menus.find((menu) => menu.label === "고객상담")
      : isSettings
        ? menus.find((menu) => menu.label === "환경설정")
      : menus.find((menu) => menu.path === currentPath));

  useEffect(() => {
    const handlePopState = () => setCurrentPath(getCurrentPath());

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function handleNavigation(event, path) {
    event.preventDefault();

    if (path !== currentPath) {
      window.history.pushState({}, "", `#${path}`);
      setCurrentPath(path);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header__inner">
          <p className="header__title">주식회사 더리모 SCM</p>
          <div className="header__identity">
            <span>{currentUser?.name}</span>
            <small>{String(currentUser?.accountType || "").toUpperCase()}</small>
            {isDevMode && <span className="header__dev-badge">DEV MODE</span>}
          </div>
          <ActiveUsersIndicator currentUser={currentUser} />
        </div>
      </header>

      <nav className="menu-bar" aria-label="주요 메뉴">
        <div className="menu-bar__scroll">
          <div className="menu-bar__inner">
            {menus.filter((menu) => menu.visible !== false && canAccess(menu.path)).map((menu) => {
              const isActive = menu.path === currentMenu?.path;

              return (
                <a
                  key={menu.path}
                  className={`menu-bar__item${isActive ? " menu-bar__item--active" : ""}`}
                  href={`#${menu.path}`}
                  aria-current={isActive ? "page" : undefined}
                  onClick={(event) => handleNavigation(event, menu.path)}
                >
                  {menu.label}
                </a>
              );
            })}
          </div>
        </div>
      </nav>

      <main className="main">
        {!canAccess(currentPath) ? (
          <PermissionState disabled />
        ) : currentPath === "/" ? (
          <HomeBusinessDashboard onNavigate={(path) => handleNavigation({ preventDefault() {} }, path)} />
        ) : isStoreManagement ? (
          <StoreManagement currentPath={currentPath} onNavigate={handleNavigation} />
        ) : isCustomerConsulting ? (
          <CustomerConsulting currentPath={currentPath} onNavigate={handleNavigation} />
        ) : currentPath === "/consultations" ? (
          <ConsultationList />
        ) : currentPath === "/as" ? (
          <AsManagement />
        ) : currentPath === "/sales" ? (
          <SalesManagement />
        ) : currentPath === "/logistics" ? (
          <LogisticsManagement />
        ) : currentPath === "/notices" ? (
          <NoticeManagement />
        ) : isSettings ? (
          <SettingsManagement currentPath={currentPath} onNavigate={(path) => handleNavigation({ preventDefault() {} }, path)} />
        ) : currentPath === "/customers" ? (
          <CustomerManagementPage />
        ) : currentPath === "/order-support" ? (
          <OrderSupportPage />
        ) : currentPath === "/memo-search" ? (
          <MemoSearchPage />
        ) : (
          <NotFoundPage onHome={() => handleNavigation({ preventDefault() {} }, "/")} />
        )}
      </main>
    </div>
  );
}

export default App;
