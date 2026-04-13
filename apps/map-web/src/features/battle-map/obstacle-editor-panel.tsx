import React, { useEffect, useSyncExternalStore } from "react";
import type { EdgeDirection } from "@limiarmap/shared-contracts";
import { useCurrentActor } from "../../services/centrifugo-client";
import { battleMapStore } from "./battle-map-store";
import {
  OBSTACLE_BRUSH_PRESETS,
  EDGE_BRUSH_PRESETS,
  getObstacleBrushPreset,
  getEdgeBrushPreset
} from "./obstacle-presets";

const panelStyle: React.CSSProperties = {
  background: "#101725",
  border: "1px solid #24324a",
  borderRadius: 6,
  padding: 12,
  display: "flex",
  flexDirection: "column",
  gap: 8
};

const buttonStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 4,
  border: "1px solid",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer"
};

export function ObstacleEditorPanel(): React.JSX.Element | null {
  const currentActor = useCurrentActor();
  const uiState = useSyncExternalStore(
    (listener) => battleMapStore.subscribe(listener),
    () => battleMapStore.getState(),
    () => battleMapStore.getState()
  );

  useEffect(() => {
    if (currentActor.actorType !== "gm" && uiState.isObstaclePaintMode) {
      battleMapStore.cancelObstaclePaint();
    }
  }, [currentActor.actorType, uiState.isObstaclePaintMode]);

  if (currentActor.actorType !== "gm") {
    return null;
  }

  const selectedPreset = getObstacleBrushPreset(uiState.obstacleBrushPresetId);
  const selectedEdgePreset = getEdgeBrushPreset(uiState.edgeBrushPresetId);
  const isBusy = Boolean(
    uiState.pendingObstaclePaintActionId || uiState.pendingEdgePaintActionId
  );

  return (
    <section style={panelStyle}>
      <div
        style={{
          fontSize: 9,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          color: "#5f7ca3"
        }}
      >
        Obstaculos
      </div>

      {!uiState.isObstaclePaintMode ? (
        <>
          <button
            type="button"
            onClick={() => battleMapStore.startObstaclePaint()}
            style={{
              ...buttonStyle,
              background: "rgba(255,146,43,0.14)",
              borderColor: "rgba(255,162,72,0.4)",
              color: "#ffb56b"
            }}
          >
            Editar obstaculos
          </button>

          <div style={{ fontSize: 11, color: "#6f86a6", lineHeight: 1.5 }}>
            Clique no mapa para pintar ou apagar circulos autoritativos de
            obstaculo.
          </div>
        </>
      ) : (
        <>
          <div style={{ fontSize: 11, color: "#d9e7ff", lineHeight: 1.5 }}>
            {uiState.obstaclePaintTarget === "edge"
              ? "Clique em uma celula para aplicar uma borda na direcao selecionada."
              : "Clique em uma celula do mapa para aplicar um circulo. Cada preset define separadamente bloqueio de movimento, visao e efeito."}
          </div>

          <div style={{ display: "flex", gap: 6 }}>
            <button
              type="button"
              onClick={() => battleMapStore.setObstaclePaintTarget("cell")}
              style={{
                ...buttonStyle,
                flex: 1,
                background:
                  uiState.obstaclePaintTarget === "cell"
                    ? "rgba(100,180,255,0.24)"
                    : "rgba(100,180,255,0.08)",
                borderColor:
                  uiState.obstaclePaintTarget === "cell"
                    ? "rgba(140,200,255,0.52)"
                    : "rgba(140,200,255,0.22)",
                color: "#a0cfff"
              }}
            >
              Celula
            </button>

            <button
              type="button"
              onClick={() => battleMapStore.setObstaclePaintTarget("edge")}
              style={{
                ...buttonStyle,
                flex: 1,
                background:
                  uiState.obstaclePaintTarget === "edge"
                    ? "rgba(100,180,255,0.24)"
                    : "rgba(100,180,255,0.08)",
                borderColor:
                  uiState.obstaclePaintTarget === "edge"
                    ? "rgba(140,200,255,0.52)"
                    : "rgba(140,200,255,0.22)",
                color: "#a0cfff"
              }}
            >
              Borda
            </button>
          </div>

          <div style={{ display: "flex", gap: 6 }}>
            <button
              type="button"
              onClick={() => battleMapStore.setObstacleBrushMode("paint")}
              style={{
                ...buttonStyle,
                flex: 1,
                background:
                  uiState.obstacleBrushMode === "paint"
                    ? "rgba(255,146,43,0.24)"
                    : "rgba(255,146,43,0.08)",
                borderColor:
                  uiState.obstacleBrushMode === "paint"
                    ? "rgba(255,176,100,0.52)"
                    : "rgba(255,176,100,0.22)",
                color: "#ffb56b"
              }}
            >
              Pintar
            </button>

            <button
              type="button"
              onClick={() => battleMapStore.setObstacleBrushMode("erase")}
              style={{
                ...buttonStyle,
                flex: 1,
                background:
                  uiState.obstacleBrushMode === "erase"
                    ? "rgba(210,84,84,0.24)"
                    : "rgba(210,84,84,0.08)",
                borderColor:
                  uiState.obstacleBrushMode === "erase"
                    ? "rgba(255,120,120,0.48)"
                    : "rgba(255,120,120,0.22)",
                color: "#f0a0a0"
              }}
            >
              Apagar
            </button>
          </div>

          {uiState.obstaclePaintTarget === "edge" && (
            <label
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 4,
                fontSize: 11,
                color: "#8ba3c7"
              }}
            >
              Direcao
              <div style={{ display: "flex", gap: 4 }}>
                {(["N", "E", "S", "W"] as EdgeDirection[]).map((dir) => (
                  <button
                    key={dir}
                    type="button"
                    onClick={() => battleMapStore.setEdgeDirection(dir)}
                    style={{
                      ...buttonStyle,
                      flex: 1,
                      background:
                        uiState.edgeDirection === dir
                          ? "rgba(255,146,43,0.24)"
                          : "rgba(255,146,43,0.08)",
                      borderColor:
                        uiState.edgeDirection === dir
                          ? "rgba(255,176,100,0.52)"
                          : "rgba(255,176,100,0.22)",
                      color: "#ffb56b"
                    }}
                  >
                    {dir}
                  </button>
                ))}
              </div>
            </label>
          )}

          {uiState.obstaclePaintTarget === "edge" ? (
            <label
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 4,
                fontSize: 11,
                color: "#8ba3c7"
              }}
            >
              Preset
              <select
                disabled={isBusy || uiState.obstacleBrushMode === "erase"}
                value={uiState.edgeBrushPresetId}
                onChange={(event) =>
                  battleMapStore.setEdgeBrushPreset(
                    event.currentTarget
                      .value as typeof uiState.edgeBrushPresetId
                  )
                }
                style={{
                  height: 34,
                  borderRadius: 4,
                  border: "1px solid rgba(110,160,220,0.35)",
                  background: "rgba(8,16,28,0.9)",
                  color: "#d8e6ff",
                  padding: "0 10px"
                }}
              >
                {EDGE_BRUSH_PRESETS.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.label}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <label
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                  fontSize: 11,
                  color: "#8ba3c7"
                }}
              >
                Preset
                <select
                  disabled={isBusy || uiState.obstacleBrushMode === "erase"}
                  value={uiState.obstacleBrushPresetId}
                  onChange={(event) =>
                    battleMapStore.setObstacleBrushPreset(
                      event.currentTarget
                        .value as typeof uiState.obstacleBrushPresetId
                    )
                  }
                  style={{
                    height: 34,
                    borderRadius: 4,
                    border: "1px solid rgba(110,160,220,0.35)",
                    background: "rgba(8,16,28,0.9)",
                    color: "#d8e6ff",
                    padding: "0 10px"
                  }}
                >
                  {OBSTACLE_BRUSH_PRESETS.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.label}
                    </option>
                  ))}
                </select>
              </label>

              <label
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                  fontSize: 11,
                  color: "#8ba3c7"
                }}
              >
                Raio do circulo
                <input
                  type="number"
                  min="0"
                  max="6"
                  step="1"
                  disabled={isBusy}
                  value={uiState.obstacleBrushRadius}
                  onChange={(event) => {
                    const parsed = Number(event.currentTarget.value);
                    if (!Number.isFinite(parsed)) {
                      return;
                    }

                    battleMapStore.setObstacleBrushRadius(
                      Math.max(0, Math.min(6, Math.round(parsed)))
                    );
                  }}
                  style={{
                    height: 34,
                    borderRadius: 4,
                    border: "1px solid rgba(110,160,220,0.35)",
                    background: "rgba(8,16,28,0.9)",
                    color: "#d8e6ff",
                    padding: "0 10px"
                  }}
                />
              </label>
            </>
          )}

          <div
            style={{
              background: "rgba(20,30,46,0.75)",
              border: "1px solid rgba(55,82,116,0.6)",
              borderRadius: 6,
              padding: "8px 10px",
              fontSize: 11,
              lineHeight: 1.6,
              color: "#d8e6ff"
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginBottom: 4
              }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 10,
                  height: 10,
                  borderRadius: 2,
                  background:
                    uiState.obstaclePaintTarget === "edge"
                      ? selectedEdgePreset.swatchColor
                      : selectedPreset.swatchColor,
                  opacity: 0.85,
                  flexShrink: 0
                }}
              />
              <strong style={{ color: "#ffcf96" }}>
                {uiState.obstaclePaintTarget === "edge"
                  ? selectedEdgePreset.label
                  : selectedPreset.label}
              </strong>
            </div>
            {uiState.obstaclePaintTarget === "edge"
              ? selectedEdgePreset.description
              : selectedPreset.description}
          </div>

          <div style={{ fontSize: 11, color: "#7d94b8", lineHeight: 1.6 }}>
            Cover é avaliado pelo sistema de targeting. Meia cobertura,
            cobertura 3/4 e cobertura total sao reportados no resultado do alvo.
            Cobertura total invalida ataques diretos.
          </div>

          <button
            type="button"
            disabled={isBusy}
            onClick={() => battleMapStore.cancelObstaclePaint()}
            style={{
              ...buttonStyle,
              background: "rgba(180,60,60,0.12)",
              borderColor: "rgba(220,100,100,0.3)",
              color: "#e49a9a",
              cursor: isBusy ? "not-allowed" : "pointer"
            }}
          >
            Fechar modo de obstaculos
          </button>
        </>
      )}
    </section>
  );
}
