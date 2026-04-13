import type { Coordinate, EdgeDirection } from "@limiarmap/shared-contracts";
import { HttpClient } from "../../services/http-client";
import { recoverRealtimeState } from "../../services/realtime-recovery";
import { battleMapStore } from "./battle-map-store";
import { getObstacleBrushPreset, getEdgeBrushPreset } from "./obstacle-presets";

const OBSTACLE_PAINT_RECOVERY_DELAY_MS = 1500;

export function submitObstaclePaint(
  sessionId: string,
  centerCell: Coordinate
): void {
  const state = battleMapStore.getState();
  if (!state.isObstaclePaintMode) {
    return;
  }

  const actionId = `obstacle:${Date.now()}`;
  const preset = getObstacleBrushPreset(state.obstacleBrushPresetId);

  battleMapStore.markObstaclePaintPending(actionId);
  battleMapStore.setMessage(
    state.obstacleBrushMode === "erase"
      ? "Removendo obstaculos..."
      : `Aplicando ${preset.label.toLowerCase()}...`
  );

  void new HttpClient()
    .submitObstaclePaint(sessionId, {
      actionId,
      sessionId,
      centerCell,
      radius: state.obstacleBrushRadius,
      mode: state.obstacleBrushMode,
      style: state.obstacleBrushMode === "paint" ? preset.style : undefined,
      knownVersion: battleMapStore.getEncounter()?.combatState.version ?? 0
    })
    .catch(() => {
      if (battleMapStore.failObstaclePaintUpdate(actionId)) {
        battleMapStore.setMessage(
          "Nao foi possivel aplicar os obstaculos. Tente novamente."
        );
      }
    });

  window.setTimeout(() => {
    if (battleMapStore.getState().pendingObstaclePaintActionId !== actionId) {
      return;
    }

    void recoverRealtimeState(
      sessionId,
      battleMapStore.getEncounter()?.combatState.version ?? 0
    )
      .then(() => {
        if (battleMapStore.failObstaclePaintUpdate(actionId)) {
          battleMapStore.setMessage(undefined);
        }
      })
      .catch(() => {
        if (battleMapStore.failObstaclePaintUpdate(actionId)) {
          battleMapStore.setMessage(
            "Nao foi possivel confirmar os obstaculos. Recarregue a pagina."
          );
        }
      });
  }, OBSTACLE_PAINT_RECOVERY_DELAY_MS);
}

export function submitEdgeObstaclePaint(
  sessionId: string,
  cell: Coordinate,
  direction: EdgeDirection
): void {
  const state = battleMapStore.getState();
  if (!state.isObstaclePaintMode || state.obstaclePaintTarget !== "edge")
    return;

  const actionId = `edge-obstacle:${Date.now()}`;
  const preset = getEdgeBrushPreset(state.edgeBrushPresetId);

  battleMapStore.markEdgePaintPending(actionId);
  battleMapStore.setMessage(
    state.obstacleBrushMode === "erase"
      ? "Removendo borda..."
      : `Aplicando ${preset.label.toLowerCase()}...`
  );

  void new HttpClient()
    .submitEdgeObstaclePaint(sessionId, {
      actionId,
      sessionId,
      cell,
      direction,
      mode: state.obstacleBrushMode,
      style: state.obstacleBrushMode === "paint" ? preset.style : undefined,
      knownVersion: battleMapStore.getEncounter()?.combatState.version ?? 0
    })
    .catch(() => {
      if (battleMapStore.failEdgePaintUpdate(actionId)) {
        battleMapStore.setMessage(
          "Nao foi possivel aplicar a borda. Tente novamente."
        );
      }
    });

  window.setTimeout(() => {
    if (battleMapStore.getState().pendingEdgePaintActionId !== actionId) return;
    void recoverRealtimeState(
      sessionId,
      battleMapStore.getEncounter()?.combatState.version ?? 0
    )
      .then(() => {
        if (battleMapStore.failEdgePaintUpdate(actionId)) {
          battleMapStore.setMessage(undefined);
        }
      })
      .catch(() => {
        if (battleMapStore.failEdgePaintUpdate(actionId)) {
          battleMapStore.setMessage(
            "Nao foi possivel confirmar as bordas. Recarregue a pagina."
          );
        }
      });
  }, OBSTACLE_PAINT_RECOVERY_DELAY_MS);
}
