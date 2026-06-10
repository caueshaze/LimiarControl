import React from "react";
import { MIN_SCALE, MAX_SCALE } from "./battle-map-camera";

interface Props {
  scale: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
}

const buttonStyle: React.CSSProperties = {
  width: 28,
  height: 28,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  border: "none",
  background: "transparent",
  color: "#cfe0f2",
  fontSize: 16,
  fontWeight: 700,
  lineHeight: 1,
  cursor: "pointer",
  borderRadius: 999
};

/** Floating +/−/reset zoom controls overlaid on the battle-map canvas. */
export function MapZoomControls({
  scale,
  onZoomIn,
  onZoomOut,
  onReset
}: Props): React.JSX.Element {
  const canZoomIn = scale < MAX_SCALE - 1e-3;
  const canZoomOut = scale > MIN_SCALE + 1e-3;

  return (
    <div
      style={{
        position: "absolute",
        right: 10,
        bottom: 10,
        display: "flex",
        alignItems: "center",
        gap: 2,
        padding: 2,
        borderRadius: 999,
        border: "1px solid rgba(120,160,210,0.35)",
        background: "rgba(12,20,32,0.72)",
        backdropFilter: "blur(4px)",
        boxShadow: "0 4px 14px rgba(0,0,0,0.35)"
      }}
    >
      <button
        type="button"
        onClick={onZoomOut}
        disabled={!canZoomOut}
        aria-label="Diminuir zoom"
        style={{ ...buttonStyle, opacity: canZoomOut ? 1 : 0.35, cursor: canZoomOut ? "pointer" : "not-allowed" }}
      >
        −
      </button>
      <button
        type="button"
        onClick={onReset}
        aria-label="Resetar zoom"
        style={{
          minWidth: 46,
          height: 28,
          border: "none",
          background: "transparent",
          color: "#cfe0f2",
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.08em",
          cursor: "pointer",
          borderRadius: 999
        }}
      >
        {`${Math.round(scale * 100)}%`}
      </button>
      <button
        type="button"
        onClick={onZoomIn}
        disabled={!canZoomIn}
        aria-label="Aumentar zoom"
        style={{ ...buttonStyle, opacity: canZoomIn ? 1 : 0.35, cursor: canZoomIn ? "pointer" : "not-allowed" }}
      >
        +
      </button>
    </div>
  );
}
