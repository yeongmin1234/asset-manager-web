import React, { useEffect, useMemo, useState } from "react";
import AnimatedBeam from "./animata/background/AnimatedBeam.jsx";

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "long",
  day: "numeric",
  weekday: "long",
});

const timeFormatter = new Intl.DateTimeFormat("ko-KR", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function LoginVisual() {
  return (
    <aside className="login-visual" aria-hidden="true">
      <AnimatedBeam />
      <div className="login-visual-overlay" />
      <LoginClock />
      <div className="login-visual-brand">
        <strong>자산관리 시스템</strong>
        <span>Asset Management System</span>
      </div>
    </aside>
  );
}

function LoginClock() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const displayTime = timeFormatter.format(now);
  const seconds = String(now.getSeconds()).padStart(2, "0");
  const displayDate = dateFormatter.format(now);
  const greeting = useMemo(() => getGreeting(now.getHours()), [now]);

  return (
    <div className="login-clock-content">
      <div className="login-clock" aria-label={`${displayTime} ${seconds}초`}>
        <span className="login-clock-main">{displayTime}</span>
        <span className="login-clock-seconds" key={seconds}>{seconds}</span>
      </div>
      <p className="login-clock-date">{displayDate}</p>
      <div className="login-clock-divider" />
      <p className="login-clock-greeting">{greeting}</p>
      <p className="login-clock-message">오늘도 좋은 하루 보내세요.</p>
    </div>
  );
}

function getGreeting(hour) {
  if (hour >= 5 && hour < 12) return "좋은 아침입니다.";
  if (hour >= 12 && hour < 18) return "좋은 오후입니다.";
  if (hour >= 18) return "좋은 저녁입니다.";
  return "좋은 밤입니다.";
}

export default React.memo(LoginVisual);
