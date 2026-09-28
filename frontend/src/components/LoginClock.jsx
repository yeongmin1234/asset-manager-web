import React, { useEffect, useState } from "react";

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

function LoginClock() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="login-clock-content" aria-label="현재 시간과 날짜">
      <span className="login-clock-time">{timeFormatter.format(now)}</span>
      <span className="login-clock-date">{dateFormatter.format(now)}</span>
    </div>
  );
}

export default LoginClock;
