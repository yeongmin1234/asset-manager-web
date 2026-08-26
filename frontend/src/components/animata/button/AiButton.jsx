import React, { useId, useMemo, useState } from "react";
import Particles, { ParticlesProvider } from "@tsparticles/react";
import { loadFull } from "tsparticles";
import "./ai-button.css";

const initializeParticles = async (engine) => loadFull(engine);

function AiButton({
  children = "로그인",
  type = "button",
  disabled = false,
  loading = false,
  className = "",
}) {
  const [isHovering, setIsHovering] = useState(false);
  const particleId = `ai-button-particles-${useId().replace(/:/g, "")}`;
  const isDisabled = disabled || loading;

  const particleOptions = useMemo(() => ({
    autoPlay: isHovering && !isDisabled,
    background: { color: { value: "transparent" } },
    detectRetina: true,
    fpsLimit: 45,
    fullScreen: { enable: false },
    interactivity: { events: { onClick: { enable: false }, onHover: { enable: false } } },
    particles: {
      color: { value: ["#ffffff", "#bfdbfe", "#c7d2fe", "#ddd6fe"] },
      move: {
        direction: "none",
        enable: true,
        outModes: { default: "out" },
        random: true,
        speed: { min: 0.35, max: 1.1 },
      },
      number: { density: { enable: false }, value: 16 },
      opacity: {
        animation: { enable: true, speed: 1.4, sync: false },
        value: { min: 0.25, max: 0.85 },
      },
      shape: { type: "star" },
      size: { value: { min: 1, max: 2.5 } },
    },
  }), [isDisabled, isHovering]);

  return (
    <div
      className={`ai-button-wrap${isHovering && !isDisabled ? " is-hovering" : ""}`}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      <ParticlesProvider init={initializeParticles}>
        <Particles id={particleId} className="ai-button-particles" options={particleOptions} />
      </ParticlesProvider>
      <button
        className={`ai-button ${className}`.trim()}
        disabled={isDisabled}
        type={type}
      >
        <span className="ai-button-content">
          {loading ? <span className="ai-button-spinner" aria-hidden="true" /> : <Sparkle className="ai-button-sparkle" />}
          <span>{loading ? "로그인 중..." : children}</span>
        </span>
        {!loading ? <Sparkle className="ai-button-mini-sparkle" /> : null}
      </button>
    </div>
  );
}

function Sparkle({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 2.8c.45 4.9 3.25 7.7 8.2 8.2-4.95.5-7.75 3.3-8.2 8.2-.45-4.9-3.25-7.7-8.2-8.2 4.95-.5 7.75-3.3 8.2-8.2Z" fill="currentColor" />
    </svg>
  );
}

export default React.memo(AiButton);
