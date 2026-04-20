import React, { useState, useSyncExternalStore } from "react";
import { useEncounterSnapshot } from "../../services/session-store";
import { useCurrentActor } from "../../services/centrifugo-client";
import { battleMapStore } from "./battle-map-store";
import { SelectedTokenCard } from "./SelectedTokenCard";
import { useBattleMapPixi } from "./use-battle-map-pixi";

export function BattleMapCanvas(): React.JSX.Element {
  const [selectedTokenId, setSelectedTokenId] = useState<string | null>(null);
  const encounter = useEncounterSnapshot();
  const currentActor = useCurrentActor();
  const uiState = useSyncExternalStore(
    (cb) => battleMapStore.subscribe(cb),
    () => battleMapStore.getState(),
    () => battleMapStore.getState(),
  );

  const selectedToken = encounter?.tokens.find((token) => token.id === selectedTokenId) ?? null;
  const selectedTokenMovementRejection = selectedTokenId != null ? (uiState.lastMovementRejectionByTokenId[selectedTokenId] ?? null) : null;
  const { containerRef, imageAspectRatio } = useBattleMapPixi({
    encounter,
    currentActor,
    uiState,
    selectedTokenId,
    setSelectedTokenId,
    selectedToken,
  });

  const cursor = uiState.isGridEditMode
    ? "grab"
    : uiState.isObstaclePaintMode
      ? "cell"
      : uiState.placingTokenId || uiState.embeddedSelectionMode !== "none" || selectedTokenId
        ? "crosshair"
        : "default";

  return (
    <div style={{ overflow: "auto", maxWidth: "100%", maxHeight: "100%" }}>
      <div style={{ position: "relative" }}>
        <div
          ref={containerRef}
          style={{
            width: "100%",
            aspectRatio: imageAspectRatio,
            borderRadius: 6,
            overflow: "hidden",
            cursor,
            backgroundColor: "#111923",
            boxShadow: "0 8px 28px rgba(0,0,0,0.35)",
            touchAction: uiState.isGridEditMode ? "none" : "auto",
          }}
        />
        {!encounter ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#666",
              fontStyle: "italic",
              pointerEvents: "none",
            }}
          >
            Aguardando dados do servidor…
          </div>
        ) : null}
        {selectedToken ? (
          <SelectedTokenCard
            selectedToken={selectedToken}
            activeCombatantId={encounter?.combatState.activeCombatantId}
            movementRejection={selectedTokenMovementRejection}
          />
        ) : null}
      </div>
    </div>
  );
}
