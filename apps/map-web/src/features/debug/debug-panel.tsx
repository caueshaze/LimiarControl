import React, { useState } from "react";
import { HttpClient } from "../../services/http-client";
import { sessionStore } from "../../services/session-store";
import {
  getCurrentActor,
  reconnectAs,
} from "../../services/centrifugo-client";
import { getMapSessionId } from "../../services/map-runtime-config";
import { battleMapStore } from "../battle-map/battle-map-store";

const btnBase: React.CSSProperties = {
  width: "100%",
  padding: "7px 10px",
  border: "1px solid",
  borderRadius: 4,
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
  textAlign: "left",
  letterSpacing: "0.02em"
};

export function DebugPanel(): React.JSX.Element {
  const [actor, setActor] = useState(getCurrentActor());
  const sessionId = getMapSessionId();

  async function handleResetBudgets(): Promise<void> {
    await fetch(`/debug/sessions/${sessionId}/reset-budgets`, { method: "POST" });
    const snapshot = await new HttpClient().fetchEncounter(sessionId);
    sessionStore.setSnapshot(snapshot);
  }

  function handleAdvanceTurn(): void {
    void new HttpClient()
      .advanceCombat(sessionId, {
        actionId: `debug-advance-${Date.now()}`,
        sessionId,
        knownVersion: sessionStore.getSnapshot()?.combatState.version ?? 0,
        requestedBy: "limiarControl"
      })
      .catch(() => {
        battleMapStore.setMessage("Nao foi possivel avancar o turno.");
      });
  }

  function handleSwitchActor(actorId: string, actorType: "player" | "gm"): void {
    reconnectAs(actorId, actorType);
    setActor({ actorId, actorType });
  }

  return (
    <div
      style={{
        background: "#0a1520",
        border: "1px solid #1e3040",
        borderRadius: 6,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8
      }}
    >
      <div
        style={{
          fontSize: 9,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          color: "#2a5070",
          marginBottom: 2
        }}
      >
        Debug
      </div>

      <button
        onClick={() => void handleResetBudgets()}
        style={{
          ...btnBase,
          background: "rgba(0,100,60,0.2)",
          borderColor: "rgba(0,180,100,0.4)",
          color: "#4caf82"
        }}
      >
        ↺ Resetar movimentos
      </button>

      <button
        onClick={handleAdvanceTurn}
        style={{
          ...btnBase,
          background: "rgba(180,120,0,0.2)",
          borderColor: "rgba(255,180,0,0.4)",
          color: "#ffc040"
        }}
      >
        ⏭ Avançar turno
      </button>

      <div style={{ borderTop: "1px solid #1a2a3a", paddingTop: 8 }}>
        <div
          style={{
            fontSize: 9,
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            color: "#2a5070",
            marginBottom: 6
          }}
        >
          Papel atual: {actor.actorType === "gm" ? "🔴 Mestre" : "🔵 Jogador"}
        </div>

        <div style={{ display: "flex", gap: 6 }}>
          <button
            onClick={() => handleSwitchActor("player_1", "player")}
            style={{
              ...btnBase,
              flex: 1,
              textAlign: "center",
              background:
                actor.actorId === "player_1"
                  ? "rgba(30,90,180,0.35)"
                  : "rgba(30,90,180,0.1)",
              borderColor:
                actor.actorId === "player_1"
                  ? "rgba(80,140,255,0.7)"
                  : "rgba(80,140,255,0.25)",
              color: actor.actorId === "player_1" ? "#7ab4ff" : "#3a6090"
            }}
          >
            Jogador
          </button>

          <button
            onClick={() => handleSwitchActor("gm_1", "gm")}
            style={{
              ...btnBase,
              flex: 1,
              textAlign: "center",
              background:
                actor.actorId === "gm_1" ? "rgba(180,30,30,0.35)" : "rgba(180,30,30,0.1)",
              borderColor:
                actor.actorId === "gm_1"
                  ? "rgba(255,80,80,0.7)"
                  : "rgba(255,80,80,0.25)",
              color: actor.actorId === "gm_1" ? "#ff8080" : "#703030"
            }}
          >
            Mestre
          </button>
        </div>
      </div>
    </div>
  );
}
