import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

const BACKGROUND_SIZE = { width: 1779, height: 884 };

function imagePointToScreen(point, width, height) {
  const scale = Math.max(width / BACKGROUND_SIZE.width, height / BACKGROUND_SIZE.height);
  return {
    x: (width - BACKGROUND_SIZE.width * scale) / 2 + point.x * BACKGROUND_SIZE.width * scale,
    y: (height - BACKGROUND_SIZE.height * scale) / 2 + point.y * BACKGROUND_SIZE.height * scale,
    scale,
  };
}

function makeLeafGeometry() {
  const positions = [0, 0, 0.6];
  const colors = [0.57, 0.26, 0.11];
  const outline = [];
  const count = 40;
  for (let i = 0; i < count; i += 1) {
    const angle = (i / count) * Math.PI * 2;
    const lobe = Math.pow(Math.max(0, Math.cos(angle * 5)), 3) * 0.24;
    const notch = 0.035 * Math.sin(angle * 13 + 0.8);
    const radius = (0.74 + lobe + notch) * (1 - 0.12 * Math.sin(angle));
    const x = Math.sin(angle) * radius * 24;
    const y = Math.cos(angle) * radius * 31;
    positions.push(x, y, 2.3 * Math.sin(angle * 2) + 3 * (x / 24) ** 2 + 1.8 * (y / 31) ** 2);
    const shade = 0.82 + 0.14 * Math.sin(angle * 3.7) + 0.08 * Math.cos(angle * 9);
    colors.push(0.66 * shade, 0.31 * shade, 0.13 * shade);
    outline.push([x, y, positions[positions.length - 1]]);
  }
  const indices = [];
  for (let i = 0; i < count; i += 1) indices.push(0, i + 1, ((i + 1) % count) + 1);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return { geometry, outline };
}

function makeLeaf(shape, index) {
  const group = new THREE.Group();
  const material = new THREE.MeshStandardMaterial({
    vertexColors: true, side: THREE.DoubleSide, roughness: 0.92, metalness: 0,
  });
  group.add(new THREE.Mesh(shape.geometry, material));

  const lines = [];
  const addLine = (a, b) => lines.push(...a, ...b);
  addLine([0, -25, 2], [0, 25, 2]);
  for (const edgeIndex of [4, 7, 12, 15, 24, 28, 33, 36]) {
    const [x, y, z] = shape.outline[edgeIndex];
    addLine([0, y * 0.42, 3], [x * 0.9, y * 0.9, z + 0.7]);
  }
  const veins = new THREE.BufferGeometry();
  veins.setAttribute("position", new THREE.Float32BufferAttribute(lines, 3));
  group.add(new THREE.LineSegments(veins, new THREE.LineBasicMaterial({ color: 0x513321, transparent: true, opacity: 0.44 })));

  const shadow = new THREE.Mesh(
    new THREE.CircleGeometry(25, 24),
    new THREE.ShaderMaterial({
      vertexShader: "varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
      fragmentShader: "varying vec2 vUv; void main() { float d = length(vUv - 0.5) * 2.0; gl_FragColor = vec4(0.18, 0.10, 0.06, (1.0 - smoothstep(0.1, 1.0, d)) * 0.13); }",
      transparent: true,
      depthWrite: false,
    }),
  );
  shadow.scale.set(1.15, 0.65, 1);
  shadow.position.set(9, -11, -11);
  group.add(shadow);
  group.userData = { index, seed: Math.random() * 100, speed: 23 + Math.random() * 17, side: index % 2 ? 1 : -1 };
  return group;
}

const steamVertex = `
  varying vec2 vUv;
  void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
`;
const steamFragment = `
  uniform float uTime;
  uniform float uAlpha;
  varying vec2 vUv;
  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1., 0.)), f.x),
               mix(hash(i + vec2(0., 1.)), hash(i + vec2(1., 1.)), f.x), f.y);
  }
  void main() {
    float y = vUv.y;
    float travel = uTime * 0.27;
    vec2 p = vec2(vUv.x * 3.1, y * 3.4 - travel);
    float warp = (noise(p * 1.6 + vec2(0.0, travel * 0.4)) - 0.5) * 0.29;
    warp += sin(y * 8.0 + uTime * 0.62) * 0.055;
    float width = mix(0.085, 0.37, y);
    float plume = 1.0 - smoothstep(width * 0.32, width, abs(vUv.x - 0.5 - warp));
    float detail = noise(p * 2.7) * 0.55 + noise(p * 5.3 + 8.7) * 0.3;
    float rise = smoothstep(0.015, 0.14, y);
    float vanish = 1.0 - smoothstep(0.56, 1.0, y);
    float alpha = plume * (0.19 + detail * 0.36) * rise * vanish * uAlpha;
    gl_FragColor = vec4(vec3(0.91, 0.89, 0.82), alpha);
  }
`;

function makeSteam() {
  const group = new THREE.Group();
  for (let i = 0; i < 2; i += 1) {
    const material = new THREE.ShaderMaterial({
      vertexShader: steamVertex,
      fragmentShader: steamFragment,
      uniforms: { uTime: { value: i * 2.7 }, uAlpha: { value: i ? 0.56 : 0.9 } },
      transparent: true, depthWrite: false, side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(155, 215), material);
    mesh.position.x = i ? 17 : -9;
    mesh.position.z = 4 + i;
    group.add(mesh);
  }
  return group;
}

export default function AutumnAtmosphere({ cupPosition = null }) {
  const hostRef = useRef(null);
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [playing, setPlaying] = useState(() => !window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [available, setAvailable] = useState(true);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => { setReducedMotion(query.matches); setPlaying(!query.matches); };
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "low-power" });
    } catch {
      setAvailable(false);
      return undefined;
    }
    renderer.setClearColor(0x000000, 0);
    host.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 1000);
    camera.position.z = 350;
    scene.add(new THREE.AmbientLight(0xffffff, 1.3));
    const sunlight = new THREE.DirectionalLight(0xffe5bd, 2.1);
    sunlight.position.set(-240, 240, 260);
    scene.add(sunlight);
    const shape = makeLeafGeometry();
    const leaves = [makeLeaf(shape, 0), makeLeaf(shape, 1)];
    leaves.forEach((leaf) => scene.add(leaf));
    const steam = makeSteam();
    scene.add(steam);
    if (!playing) {
      leaves.forEach((leaf) => { leaf.visible = false; });
      steam.visible = false;
    }
    let width = 0; let height = 0; let mobile = false;
    const resize = () => {
      const rect = host.getBoundingClientRect();
      width = rect.width; height = rect.height;
      mobile = width < 700;
      camera.left = -width / 2; camera.right = width / 2;
      camera.top = height / 2; camera.bottom = -height / 2;
      camera.updateProjectionMatrix();
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobile ? 1 : 1.5));
      renderer.setSize(width, height, false);
      leaves[0].visible = playing;
      leaves[1].visible = playing && !mobile;
      if (cupPosition) {
        const cup = imagePointToScreen(cupPosition, width, height);
        steam.position.set(cup.x - width / 2, height / 2 - cup.y + 107 * cup.scale, 0);
        steam.scale.setScalar(Math.min(1.3, Math.max(0.7, cup.scale)));
        steam.visible = playing && cup.x > -30 && cup.x < width + 30 && cup.y > 0 && cup.y < height;
      } else steam.visible = false;
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();
    let frame = 0; let last = 0; let time = 0;
    const animate = (stamp) => {
      frame = requestAnimationFrame(animate);
      if (stamp - last < (mobile ? 42 : 33)) return;
      const delta = Math.min((stamp - (last || stamp)) / 1000, 0.07);
      last = stamp; time += delta;
      leaves.forEach((leaf, index) => {
        const data = leaf.userData;
        if (index && mobile) return;
        if (!leaf.userData.initialized || leaf.position.y < -height / 2 - 55) {
          leaf.userData.initialized = true;
          leaf.position.y = height / 2 + 40 + Math.random() * 170 + index * 140;
          leaf.position.x = data.side * (width * (0.34 + Math.random() * 0.11));
          data.seed = Math.random() * 100;
          data.speed = 22 + Math.random() * 20;
        }
        leaf.position.y -= data.speed * delta;
        leaf.position.x += (Math.sin(time * 0.7 + data.seed) * 5 + data.side * Math.sin(time * 0.29 + data.seed) * 2) * delta;
        leaf.rotation.set(
          Math.sin(time * 0.82 + data.seed) * 0.75,
          time * (data.side * 0.47) + data.seed,
          Math.sin(time * 0.48 + data.seed) * 0.38,
        );
        leaf.scale.setScalar((mobile ? 0.68 : 0.86) + index * 0.12);
      });
      steam.children.forEach((mesh) => { mesh.material.uniforms.uTime.value = time + mesh.position.x * 0.14; });
      renderer.render(scene, camera);
    };
    const updateVisibility = () => {
      cancelAnimationFrame(frame);
      if (playing && !document.hidden) {
        last = 0;
        frame = requestAnimationFrame(animate);
      }
    };
    document.addEventListener("visibilitychange", updateVisibility);
    if (playing && !document.hidden) frame = requestAnimationFrame(animate);
    else renderer.render(scene, camera);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("visibilitychange", updateVisibility);
      observer.disconnect();
      scene.traverse((object) => {
        if (object.geometry && object.geometry !== shape.geometry) object.geometry.dispose();
        if (object.material) object.material.dispose();
      });
      shape.geometry.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, [playing, cupPosition]);

  return (
    <>
      <div className="login-atmosphere" ref={hostRef} aria-hidden="true" />
      {available && (
        <button className="login-motion-toggle" type="button" onClick={() => setPlaying((value) => !value)} aria-pressed={playing}>
          {playing ? "애니메이션 정지" : "애니메이션 재생"}
        </button>
      )}
      {reducedMotion && <span className="visually-hidden">시스템의 동작 줄이기 설정에 따라 애니메이션이 정지되었습니다.</span>}
    </>
  );
}
