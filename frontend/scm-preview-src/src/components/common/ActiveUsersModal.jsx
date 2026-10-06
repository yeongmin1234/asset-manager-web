import React from "react";
import { Modal, StatusBadge } from "./CommonUI";

export default function ActiveUsersModal({
  users,
  refreshedAt,
  refreshing,
  onRefresh,
  onClose,
}) {
  return (
    <Modal title="현재 접속자" onClose={onClose} className="active-users-dialog">
      <div className="active-users-modal">
        <div className="active-users-summary">
          <div>
            <span>현재 접속자</span>
            <strong>{users.length}명</strong>
          </div>
          <p>마지막 갱신 <time dateTime={refreshedAt.iso}>{refreshedAt.label}</time></p>
          <button type="button" disabled={refreshing} onClick={onRefresh}>
            {refreshing ? "갱신 중" : "새로고침"}
          </button>
        </div>
        <div className="active-users-table-wrap">
          <table>
            <colgroup>
              <col style={{ width: "16%" }} />
              <col style={{ width: "16%" }} />
              <col style={{ width: "24%" }} />
              <col style={{ width: "16%" }} />
              <col style={{ width: "18%" }} />
              <col style={{ width: "10%" }} />
            </colgroup>
            <thead>
              <tr>
                <th>부서</th>
                <th>계정 유형</th>
                <th>현재 화면</th>
                <th>접속 시각</th>
                <th>최근 활동</th>
                <th>상태</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td title={user.department}>{user.department}</td>
                  <td title={user.accountType}>{user.accountType}</td>
                  <td title={user.currentPage}>{user.currentPage}</td>
                  <td title={`${user.connectedAt} 접속`}>{user.connectedAt} 접속</td>
                  <td title={user.lastActiveAt}>{user.lastActiveAt}</td>
                  <td title={user.status}><StatusBadge status={user.status} /></td>
                </tr>
              ))}
              {!users.length && <tr><td className="active-users-empty" colSpan={6}>실시간 접속자 연동 준비 중입니다.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </Modal>
  );
}
