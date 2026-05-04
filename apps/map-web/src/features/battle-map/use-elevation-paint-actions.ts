import type { Coordinate } from "@limiarmap/shared-contracts";
import { HttpClient } from "../../services/http-client";
import { recoverRealtimeState } from "../../services/realtime-recovery";
import { battleMapStore } from "./battle-map-store";

const ELEVATION_PAINT_RECOVERY_DELAY_MS = 1500;

export function submitElevationPaint(
  sessionId: string,
  centerCell: Coordinate
): void {
  const state = battleMapStore.getState();
  if (!state.isElevationPaintMode) {
    return;
  }

  const actionId = `elevation:${Date.now()}`;

  battleMapStore.markElevationPaintPending(actionId);
  battleMapStore.setMessage(
    state.elevationBrushMode === "erase"
      ? "Removendo elevação..."
      : `Aplicando elevação ${state.elevationBrushPresetMeters}m...`
  );

  void new HttpClient()
    .submitElevationPaint(sessionId, {
      actionId,
      sessionId,
      centerCell,
      radius: state.elevationBrushRadius,
      mode: state.elevationBrushMode,
      elevationMeters: state.elevationBrushMode === "paint" ? state.elevationBrushPresetMeters : undefined,
      knownVersion: battleMapStore.getEncounter()?.combatState.version ?? 0
    })
    .catch(() => {
      if (battleMapStore.failElevationPaintUpdate(actionId)) {
        battleMapStore.setMessage(
          "Nao foi possivel aplicar a elevação. Tente novamente."
        );
      }
    });

  window.setTimeout(() => {
    if (battleMapStore.getState().pendingElevationPaintActionId !== actionId) {
      return;
    }

    void recoverRealtimeState(
      sessionId,
      battleMapStore.getEncounter()?.combatState.version ?? 0
    )
      .then(() => {
        if (battleMapStore.failElevationPaintUpdate(actionId)) {
          battleMapStore.setMessage(undefined);
        }
      })
      .catch(() => {
        if (battleMapStore.failElevationPaintUpdate(actionId)) {
          battleMapStore.setMessage(
            "Nao foi possivel confirmar a elevação. Recarregue a pagina."
          );
        }
      });
  }, ELEVATION_PAINT_RECOVERY_DELAY_MS);
}
