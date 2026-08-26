import React from "react";
import "./animated-beam.css";

const LANES = 64;

const prand = (n) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

const lerp = (min, max, t) => min + (max - min) * t;

const beamIndexes = Array.from({ length: LANES }, (_, index) => index);

function Beam({ index }) {
  const fast = prand(index + 91) < 0.3;
  const duration = fast
    ? lerp(1.2, 3.2, prand(index))
    : lerp(6, 14, prand(index));
  const delay = lerp(0, 9, prand(index + 13));
  const length = Math.round(lerp(24, 84, prand(index + 29)));
  const width = Math.round(lerp(3, 7, prand(index + 53)));
  const opacity = fast
    ? lerp(0.62, 0.88, prand(index + 71))
    : lerp(0.22, 0.58, prand(index + 71));

  return (
    <div className="ab-lane">
      <div
        className="ab-beam"
        style={{
          "--duration": `${duration.toFixed(2)}s`,
          "--delay": `${delay.toFixed(2)}s`,
          "--length": `${length}px`,
          "--opacity": opacity.toFixed(2),
          width: `${width}px`,
        }}
      >
        <div className="ab-beam-streak" />
      </div>
    </div>
  );
}

function AnimatedBeam({ className = "" }) {
  return (
    <div className={`animated-beam ${className}`.trim()} aria-hidden="true">
      <div className="ab-lanes">
        {beamIndexes.map((index) => <Beam index={index} key={index} />)}
      </div>
    </div>
  );
}

export default React.memo(AnimatedBeam);
