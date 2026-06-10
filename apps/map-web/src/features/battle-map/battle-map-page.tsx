import React, { useEffect, useState, useSyncExternalStore } from "react";
import { HttpClient } from "../../services/http-client";
import { sessionStore } from "../../services/session-store";
import { connectSessionRealtime } from "../../services/centrifugo-client";
import {
  applyEmbeddedMapContext,
  isEmbeddedMapContextMessage,
  postEmbeddedMapReady,
} from "../../services/embedded-map-bridge";
import { BattleMapCanvas } from "./battle-map-canvas";
import { TokenPlacementBar } from "./token-placement-bar";
import { battleMapStore } from "./battle-map-store";
import { GridCalibrationPanel } from "./grid-calibration-panel";
import { ObstacleEditorPanel } from "./obstacle-editor-panel";
import { ElevationEditorPanel } from "./elevation-editor-panel";
import { CombatPanel } from "../combat/combat-panel";
import { DebugPanel } from "../debug/debug-panel";
import { getMapSessionId, isEmbeddedMapView } from "../../services/map-runtime-config";
import { useIsNarrow } from "../../services/use-is-narrow";

function formatEncounterLoadError(error: unknown): string {
  if (error && typeof error === "object" && "status" in error) {
    const typedError = error as { status?: unknown; message?: unknown };
    if (typedError.status === 404) {
      return "O combate ainda nao foi sincronizado com o servidor do mapa. Reabra o modo de combate ou tente novamente em instantes.";
    }
    if (typeof typedError.message === "string" && typedError.message.trim()) {
      return typedError.message;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Nao foi possivel carregar o encontro tatico.";
}

export function BattleMapPage(): React.JSX.Element {
  const sessionId = getMapSessionId();
  const embedded = isEmbeddedMapView();
  const [loadError, setLoadError] = useState<string | null>(null);
  const isNarrow = useIsNarrow();
  const [panelOpen, setPanelOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    sessionStore.clearSnapshot();
    setLoadError(null);
    const disconnectRealtime = connectSessionRealtime(sessionId);
    new HttpClient()
      .fetchEncounter(sessionId)
      .then((snapshot) => {
        if (cancelled) {
          return;
        }
        sessionStore.setSnapshot(snapshot);
        setLoadError(null);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        sessionStore.clearSnapshot();
        setLoadError(formatEncounterLoadError(error));
      });
    return () => {
      cancelled = true;
      disconnectRealtime();
      sessionStore.clearSnapshot();
    };
  }, [sessionId]);

  useEffect(() => {
    if (!embedded) {
      return;
    }

    const handleMessage = (event: MessageEvent) => {
      if (!isEmbeddedMapContextMessage(event.data)) {
        return;
      }
      if (event.data.payload.sessionId !== sessionId) {
        return;
      }
      applyEmbeddedMapContext(event.data.payload);
    };

    window.addEventListener("message", handleMessage);
    postEmbeddedMapReady(sessionId);

    return () => {
      window.removeEventListener("message", handleMessage);
      battleMapStore.clearEmbeddedInteraction();
    };
  }, [embedded, sessionId]);

  const message = useSyncExternalStore(
    (cb) => battleMapStore.subscribe(cb),
    () => battleMapStore.getState().message,
    () => battleMapStore.getState().message
  );

  if (embedded) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          overflow: "hidden",
          background: "#0f0f1a",
          padding: 12,
          gap: 8,
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: "#6e85a5",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          {`LimiarMap · ${sessionId}`}
        </div>
        <TokenPlacementBar />
        {message ? (
          <div
            style={{
              background: "rgba(200,60,60,0.15)",
              border: "1px solid rgba(200,60,60,0.4)",
              borderRadius: 8,
              padding: "8px 10px",
              fontSize: 12,
              color: "#f48080",
              lineHeight: 1.4,
            }}
          >
            {message}
          </div>
        ) : null}
        {loadError ? (
          <div
            style={{
              background: "rgba(200,60,60,0.15)",
              border: "1px solid rgba(200,60,60,0.4)",
              borderRadius: 8,
              padding: "8px 10px",
              fontSize: 12,
              color: "#f9b3b3",
              lineHeight: 1.5,
            }}
          >
            {loadError}
          </div>
        ) : null}
        <div style={{ flex: 1, minHeight: 0 }}>
          <BattleMapCanvas />
        </div>
      </div>
    );
  }

  const sidePanelContent = (
    <>
      <CombatPanel />

      {message && (
        <div
          style={{
            background: "rgba(200,60,60,0.15)",
            border: "1px solid rgba(200,60,60,0.4)",
            borderRadius: 5,
            padding: "8px 10px",
            fontSize: 12,
            color: "#f48080",
            lineHeight: 1.4
          }}
        >
          {message}
        </div>
      )}
      {loadError ? (
        <div
          style={{
            background: "rgba(200,60,60,0.15)",
            border: "1px solid rgba(200,60,60,0.4)",
            borderRadius: 5,
            padding: "8px 10px",
            fontSize: 12,
            color: "#f9b3b3",
            lineHeight: 1.5,
          }}
        >
          {loadError}
        </div>
      ) : null}

      <DebugPanel />
      <GridCalibrationPanel />
      <ObstacleEditorPanel />
      <ElevationEditorPanel />

      <div
        style={{
          marginTop: "auto",
          fontSize: 10,
          color: "#2a3a4a",
          borderTop: "1px solid #1a2a3a",
          paddingTop: 8,
          lineHeight: 1.8
        }}
      >
        <div>■ Azul = jogador · Vermelho = mestre</div>
        <div>Borda dourada = turno ativo</div>
        <div>Borda verde = selecionado</div>
        <div>Célula laranja = bloqueia movimento</div>
        <div>Célula roxa = bloqueia spell</div>
        <div>Célula dourada = cobertura</div>
        <div>Célula vermelha = parede completa</div>
      </div>
    </>
  );

  const mapArea = (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        overflow: "auto",
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: "#3a5070",
          letterSpacing: "0.1em",
          textTransform: "uppercase"
        }}
      >
        {`LimiarMap · ${sessionId}`}
      </div>
      <TokenPlacementBar />
      <BattleMapCanvas />
    </div>
  );

  // Narrow viewports (phones): stack vertically and move the side panel into a
  // collapsible bottom sheet so the map gets the full width.
  if (isNarrow) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", background: "#0f0f1a" }}>
        {mapArea}
        <div style={{ borderTop: "1px solid #1a2a3a", background: "#0c0c18", flexShrink: 0 }}>
          <button
            type="button"
            onClick={() => setPanelOpen((open) => !open)}
            aria-expanded={panelOpen}
            style={{
              width: "100%",
              padding: "10px 14px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              border: "none",
              background: "transparent",
              color: "#b5c4d8",
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              cursor: "pointer"
            }}
          >
            <span>Painel de combate</span>
            <span>{panelOpen ? "▼" : "▲"}</span>
          </button>
          {panelOpen ? (
            <div
              style={{
                maxHeight: "60vh",
                overflowY: "auto",
                padding: 12,
                display: "flex",
                flexDirection: "column",
                gap: 12
              }}
            >
              {sidePanelContent}
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#0f0f1a" }}>
      {/* Map area */}
      {mapArea}

      {/* Side panel */}
      <div
        style={{
          width: 260,
          borderLeft: "1px solid #1a2a3a",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          overflowY: "auto",
          background: "#0c0c18",
          flexShrink: 0
        }}
      >
        {sidePanelContent}
      </div>
    </div>
  );
}
