import React from "react";
import { formatMovementSpeedCellsAsMeters, formatPathCostUnitsAsMeters } from "../../services/movement-metrics";
import { getConditionIndicators } from "../conditions/condition-indicators";
import { getTokenBadgeLabel } from "./utils";

type Props = {
  selectedToken: {
    id: string;
    label: string;
    controllerType: string;
    controllerId: string;
    movementBudget: number;
    movementSpeedCells: number;
    combatantId?: string | null;
    conditions?: string[];
  };
  activeCombatantId?: string | null;
  movementRejection: {
    reason: string;
    message: string;
    pathCostUnits?: number;
    movementBudget?: number;
    exceededBy?: number;
  } | null;
};

export function SelectedTokenCard({ selectedToken, activeCombatantId, movementRejection }: Props): React.JSX.Element {
  return (
    <div
      style={{
        position: "absolute",
        right: 12,
        bottom: 12,
        width: "min(320px, calc(100% - 24px))",
        borderRadius: 12,
        border: "1px solid rgba(148,163,184,0.22)",
        background: "linear-gradient(180deg, rgba(15,23,42,0.88), rgba(2,6,23,0.94))",
        boxShadow: "0 18px 40px rgba(2, 6, 23, 0.38)",
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        pointerEvents: "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "999px",
            display: "grid",
            placeItems: "center",
            background: selectedToken.controllerType === "player" ? "rgba(59,130,246,0.22)" : "rgba(239,68,68,0.22)",
            border: "1px solid rgba(255,255,255,0.16)",
            color: "#f8fafc",
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: "0.08em",
          }}
        >
          {getTokenBadgeLabel(selectedToken.label)}
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ color: "#f8fafc", fontSize: 14, fontWeight: 700 }}>{selectedToken.label}</div>
          <div style={{ color: "#94a3b8", fontSize: 11 }}>
            {selectedToken.controllerType === "gm" ? "Controlado pelo mestre" : `Controlado pelo player ${selectedToken.controllerId}`}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
        <div style={{ borderRadius: 10, background: "rgba(15,23,42,0.64)", padding: "8px 10px" }}>
          <div style={{ color: "#64748b", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Movimento</div>
          <div style={{ color: "#e2e8f0", fontSize: 14, fontWeight: 700 }}>
            {formatPathCostUnitsAsMeters(selectedToken.movementBudget)} / {formatMovementSpeedCellsAsMeters(selectedToken.movementSpeedCells)} m
          </div>
        </div>
        <div style={{ borderRadius: 10, background: "rgba(15,23,42,0.64)", padding: "8px 10px" }}>
          <div style={{ color: "#64748b", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Turno</div>
          <div
            style={{
              color: selectedToken.combatantId != null && selectedToken.combatantId === activeCombatantId ? "#facc15" : "#cbd5e1",
              fontSize: 14,
              fontWeight: 700,
            }}
          >
            {selectedToken.combatantId != null && selectedToken.combatantId === activeCombatantId ? "Ativo" : "Aguardando"}
          </div>
        </div>
      </div>

      {(selectedToken.conditions ?? []).length > 0 ? (
        <div
          style={{
            borderRadius: 10,
            background: "rgba(15,23,42,0.64)",
            padding: "8px 10px",
            display: "flex",
            flexDirection: "column",
            gap: 5,
          }}
        >
          <div style={{ color: "#64748b", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Condições</div>
          {getConditionIndicators(selectedToken.conditions ?? []).map((indicator) => (
            <div key={indicator.conditionType} style={{ display: "flex", alignItems: "center", gap: 7 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: indicator.colorToken, flexShrink: 0 }} />
              <span style={{ color: indicator.colorToken, fontSize: 12, fontWeight: 600 }}>{indicator.label}</span>
            </div>
          ))}
        </div>
      ) : null}

      {movementRejection ? (
        <div
          style={{
            borderRadius: 10,
            border: movementRejection.reason === "movement_budget_exceeded" ? "1px solid rgba(248,113,113,0.42)" : "1px solid rgba(251,191,36,0.32)",
            background: movementRejection.reason === "movement_budget_exceeded" ? "rgba(127,29,29,0.22)" : "rgba(120,53,15,0.18)",
            padding: "10px 12px",
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          <div style={{ color: "#fca5a5", fontSize: 11, fontWeight: 700 }}>{movementRejection.message}</div>
          {movementRejection.pathCostUnits !== undefined || movementRejection.movementBudget !== undefined ? (
            <div style={{ color: "#fecaca", fontSize: 12, lineHeight: 1.5 }}>
              {movementRejection.movementBudget !== undefined ? `Disponivel: ${formatPathCostUnitsAsMeters(movementRejection.movementBudget)} m. ` : ""}
              {movementRejection.pathCostUnits !== undefined ? `Tentativa: ${formatPathCostUnitsAsMeters(movementRejection.pathCostUnits)} m. ` : ""}
              {movementRejection.exceededBy !== undefined ? `Excedente: ${formatPathCostUnitsAsMeters(movementRejection.exceededBy)} m.` : ""}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
