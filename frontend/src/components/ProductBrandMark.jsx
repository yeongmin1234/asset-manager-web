import { useEffect, useRef, useState } from "react";
import { imagePointToScreen } from "./loginBackgroundLayout.js";

const PRODUCTS = [
  { id: "toaster", point: { x: 0.283, y: 0.806 }, width: 61 },
  { id: "lantern", point: { x: 0.874, y: 0.833 }, width: 39 },
];

export default function ProductBrandMark() {
  const layerRef = useRef(null);
  const [viewport, setViewport] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setViewport({ width, height });
    });
    observer.observe(layer);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="login-product-brand-layer" ref={layerRef} aria-hidden="true">
      {PRODUCTS.map((product) => {
        const position = imagePointToScreen(product.point, viewport.width, viewport.height);
        const markWidth = product.width * position.scale;
        const visible = viewport.width > 0 && position.x - markWidth / 2 > 0 && position.x + markWidth / 2 < viewport.width
          && position.y > 0 && position.y < viewport.height;
        return visible ? (
          <span
            className={`login-product-brand login-product-brand--${product.id}`}
            key={product.id}
            style={{ left: position.x, top: position.y, width: markWidth, fontSize: (product.id === "toaster" ? 9 : 5.8) * position.scale }}
          >BALMUDA</span>
        ) : null;
      })}
    </div>
  );
}
