import React, { useMemo, useState } from "react";
import ActiveUsersModal from "../common/ActiveUsersModal";
import { getActiveUsers } from "../../services/activeUsersService";
import { getAccountTypeLabel } from "../../constants/accountTypes";

function formatRefreshTime(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return {
    iso: date.toISOString(),
    label: `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`,
  };
}

export default function ActiveUsersIndicator({ currentUser }) {
  const [open, setOpen] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshedAt, setRefreshedAt] = useState(() => formatRefreshTime(new Date()));
  const users = useMemo(() => {
    const refreshedActivities = ["방금 전", "방금 전", "1분 전", "5분 전"];
    return getActiveUsers().filter((user) => user.id !== "mock-current-user" || currentUser.status === "active").map((user, index) => ({
      ...user,
      name: user.id === "mock-current-user" ? currentUser.name : user.name,
      account: user.id === "mock-current-user" ? currentUser.account : user.account,
      department: user.id === "mock-current-user" ? currentUser.department : user.department,
      accountType: user.id === "mock-current-user" ? getAccountTypeLabel(currentUser.accountType) : user.accountType,
      lastActiveAt: refreshVersion > 0 ? refreshedActivities[index] : user.lastActiveAt,
    }));
  }, [currentUser, refreshVersion]);
  const count = users.length;

  function refreshData() {
    if (refreshing) return;
    setRefreshing(true);
    window.setTimeout(() => {
      setRefreshVersion((version) => version + 1);
      setRefreshedAt(formatRefreshTime(new Date()));
      setRefreshing(false);
    }, 250);
  }

  return (
    <>
      <button
        type="button"
        className="active-users-indicator"
        title="현재 시스템 접속자"
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        <span className="active-users-indicator__dot" aria-hidden="true" />
        <span className="active-users-indicator__icon" aria-hidden="true">👥</span>
        <span className="active-users-indicator__wide">{count ? <>현재 접속 <strong>{count}</strong>명</> : "실시간 접속자 연동 준비 중"}</span>
        <span className="active-users-indicator__compact">{count ? <>접속 <strong>{count}</strong></> : "접속 준비 중"}</span>
      </button>
      {open && (
        <ActiveUsersModal
          users={users}
          refreshedAt={refreshedAt}
          refreshing={refreshing}
          onRefresh={refreshData}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
