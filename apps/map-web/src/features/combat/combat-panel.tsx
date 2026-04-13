import React from "react";
import { useEncounterSnapshot } from "../../services/session-store";
import {
  formatMeters,
  formatPathCostUnitsAsMeters,
  movementSpeedCellsToMeters,
  pathCostUnitsToMeters,
} from "../../services/movement-metrics";

const panelStyle: React.CSSProperties = {
  background: "#16213e",
  border: "1px solid #2a3a5e",
  borderRadius: 6,
  padding: 14,
  display: "flex",
  flexDirection: "column",
  gap: 10
};

const labelStyle: React.CSSProperties = {
  fontSize: 10,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  color: "#607090",
  marginBottom: 2
};

const valueStyle: React.CSSProperties = {
  fontSize: 15,
  fontWeight: 600,
  color: "#e0e8ff"
};

function BudgetBar({ current, max }: { current: number; max: number }): React.JSX.Element {
  const pct = max > 0 ? Math.max(0, (current / max) * 100) : 0;
  const color = pct > 60 ? "#4caf50" : pct > 25 ? "#ff9800" : "#f44336";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ ...labelStyle }}>Movimento restante</div>
      <div
        style={{
          height: 8,
          borderRadius: 4,
          background: "#1a1a2e",
          overflow: "hidden"
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: color,
            borderRadius: 4,
            transition: "width 0.3s ease"
          }}
        />
      </div>
      <div style={{ fontSize: 12, color: color }}>
        {formatMeters(current)} / {formatMeters(max)} m
      </div>
    </div>
  );
}

export function CombatPanel(): React.JSX.Element {
  const encounter = useEncounterSnapshot();

  if (!encounter) {
    return (
      <div style={panelStyle}>
        <span style={{ color: "#555" }}>Carregando combate…</span>
      </div>
    );
  }

  const { combatState, tokens } = encounter;
  const activeToken = tokens.find((t) => t.combatantId === combatState.activeCombatantId);

  return (
    <div style={panelStyle}>
      <div>
        <div style={labelStyle}>Rodada</div>
        <div style={valueStyle}>{combatState.roundNumber}</div>
      </div>

      <div>
        <div style={labelStyle}>Combatente ativo</div>
        <div
          style={{
            ...valueStyle,
            color: "#ffd700",
            display: "flex",
            alignItems: "center",
            gap: 6
          }}
        >
          <span
            style={{
              display: "inline-block",
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: "#ffd700",
              boxShadow: "0 0 6px #ffd700",
              flexShrink: 0
            }}
          />
          {activeToken?.label ?? combatState.activeCombatantId ?? "—"}
        </div>
      </div>

      {activeToken && (
        <BudgetBar
          current={pathCostUnitsToMeters(activeToken.movementBudget)}
          max={movementSpeedCellsToMeters(activeToken.movementSpeedCells)}
        />
      )}

      <div style={{ borderTop: "1px solid #1e2d4a", paddingTop: 8 }}>
        <div style={labelStyle}>Tokens</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 5, marginTop: 4 }}>
          {tokens.map((t) => {
            const isActive = t.combatantId === combatState.activeCombatantId;
            return (
              <div
                key={t.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "4px 6px",
                  borderRadius: 4,
                  background: isActive ? "rgba(255,215,0,0.08)" : "transparent",
                  border: isActive ? "1px solid rgba(255,215,0,0.2)" : "1px solid transparent"
                }}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background:
                      t.controllerType === "player"
                        ? "#2a7abf"
                        : t.controllerType === "gm"
                          ? "#bf3030"
                          : "#2d7a3a",
                    flexShrink: 0
                  }}
                />
                <span style={{ flex: 1, color: isActive ? "#ffd700" : "#c0c8d8", fontSize: 13 }}>
                  {t.label}
                </span>
                <span style={{ fontSize: 11, color: "#607090" }}>
                  ({t.position.x},{t.position.y})
                </span>
                <span
                  style={{
                    fontSize: 11,
                    color: t.movementBudget > 0 ? "#4caf50" : "#f44336",
                    minWidth: 42,
                    textAlign: "right"
                  }}
                >
                  {formatPathCostUnitsAsMeters(t.movementBudget)} m
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ borderTop: "1px solid #1e2d4a", paddingTop: 8 }}>
        <div style={labelStyle}>Versão autoritativa</div>
        <div style={{ fontSize: 12, color: "#607090", fontFamily: "monospace" }}>
          v{combatState.version}
        </div>
      </div>
    </div>
  );
}
