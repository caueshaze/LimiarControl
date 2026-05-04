import React, { useEffect, useSyncExternalStore } from "react";
import { useCurrentActor } from "../../services/centrifugo-client";
import { battleMapStore } from "./battle-map-store";
import { ELEVATION_PRESETS, getElevationPreset } from "./elevation-presets";

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

export function ElevationEditorPanel(): React.JSX.Element | null {
  const currentActor = useCurrentActor();
  const uiState = useSyncExternalStore(
    (listener) => battleMapStore.subscribe(listener),
    () => battleMapStore.getState(),
    () => battleMapStore.getState()
  );

  useEffect(() => {
    if (currentActor.actorType !== "gm" && uiState.isElevationPaintMode) {
      battleMapStore.cancelElevationPaint();
    }
  }, [currentActor.actorType, uiState.isElevationPaintMode]);

  if (currentActor.actorType !== "gm") {
    return null;
  }

  const selectedPreset = getElevationPreset(uiState.elevationBrushPresetMeters);
  const isBusy = Boolean(uiState.pendingElevationPaintActionId);

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
        Elevação
      </div>

      {!uiState.isElevationPaintMode ? (
        <>
          <button
            type="button"
            onClick={() => battleMapStore.startElevationPaint()}
            style={{
              ...buttonStyle,
              background: "rgba(139,92,246,0.14)",
              borderColor: "rgba(167,139,250,0.4)",
              color: "#c4b5fd"
            }}
          >
            Editar elevação
          </button>

          <div style={{ fontSize: 11, color: "#6f86a6", lineHeight: 1.5 }}>
            Clique no mapa para pintar altura por célula.
          </div>
        </>
      ) : (
        <>
          <div style={{ fontSize: 11, color: "#d9e7ff", lineHeight: 1.5 }}>
            Clique em uma célula do mapa para aplicar a altura selecionada.
          </div>

          <div style={{ display: "flex", gap: 6 }}>
            <button
              type="button"
              onClick={() => battleMapStore.setElevationBrushMode("paint")}
              style={{
                ...buttonStyle,
                flex: 1,
                background:
                  uiState.elevationBrushMode === "paint"
                    ? "rgba(139,92,246,0.24)"
                    : "rgba(139,92,246,0.08)",
                borderColor:
                  uiState.elevationBrushMode === "paint"
                    ? "rgba(167,139,250,0.52)"
                    : "rgba(167,139,250,0.22)",
                color: "#c4b5fd"
              }}
            >
              Pintar
            </button>

            <button
              type="button"
              onClick={() => battleMapStore.setElevationBrushMode("erase")}
              style={{
                ...buttonStyle,
                flex: 1,
                background:
                  uiState.elevationBrushMode === "erase"
                    ? "rgba(210,84,84,0.24)"
                    : "rgba(210,84,84,0.08)",
                borderColor:
                  uiState.elevationBrushMode === "erase"
                    ? "rgba(255,120,120,0.48)"
                    : "rgba(255,120,120,0.22)",
                color: "#f0a0a0"
              }}
            >
              Apagar
            </button>
          </div>

          <label
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 4,
              fontSize: 11,
              color: "#8ba3c7"
            }}
          >
            Altura
            <select
              disabled={isBusy || uiState.elevationBrushMode === "erase"}
              value={uiState.elevationBrushPresetMeters}
              onChange={(event) =>
                battleMapStore.setElevationBrushPreset(
                  Number(event.currentTarget.value)
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
              {ELEVATION_PRESETS.map((preset) => (
                <option key={preset.meters} value={preset.meters}>
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
            Raio do círculo
            <input
              type="number"
              min="0"
              max="6"
              step="1"
              disabled={isBusy}
              value={uiState.elevationBrushRadius}
              onChange={(event) => {
                const parsed = Number(event.currentTarget.value);
                if (!Number.isFinite(parsed)) {
                  return;
                }

                battleMapStore.setElevationBrushRadius(
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
                  background: selectedPreset.swatchColor,
                  opacity: 0.85,
                  flexShrink: 0
                }}
              />
              <strong style={{ color: "#c4b5fd" }}>
                {selectedPreset.label}
              </strong>
            </div>
            {uiState.elevationBrushMode === "erase"
              ? "Remove a elevação das células selecionadas (volta para 0m)."
              : `Aplica ${selectedPreset.label} nas células selecionadas.`}
          </div>

          <button
            type="button"
            disabled={isBusy}
            onClick={() => battleMapStore.cancelElevationPaint()}
            style={{
              ...buttonStyle,
              background: "rgba(180,60,60,0.12)",
              borderColor: "rgba(220,100,100,0.3)",
              color: "#e49a9a",
              cursor: isBusy ? "not-allowed" : "pointer"
            }}
          >
            Fechar modo de elevação
          </button>
        </>
      )}
    </section>
  );
}
