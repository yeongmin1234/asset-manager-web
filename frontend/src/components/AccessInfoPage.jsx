import React from "react";
import NetworkCredentialPage from "./NetworkCredentialPage.jsx";


export default function AccessInfoPage({ currentUser }) {
  return (
    <>
      <div className="portal-screen-heading network-status-heading">
        <div>
          <h2>접속정보 관리</h2>
          <p>서버 및 시스템 접속정보를 관리합니다.</p>
        </div>
      </div>
      <NetworkCredentialPage currentUser={currentUser} />
    </>
  );
}
