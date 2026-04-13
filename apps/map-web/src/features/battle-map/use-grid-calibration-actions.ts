import type { GridCalibration } from "@limiarmap/shared-contracts";
import { HttpClient } from "../../services/http-client";
import { battleMapStore } from "./battle-map-store";

export function submitGridCalibration(
  sessionId: string,
  gridCalibration: GridCalibration,
  gridWidth: number,
  gridHeight: number
): void {
  const actionId = `grid-calibration:${Date.now()}`;
  battleMapStore.markGridCalibrationPending(actionId);
  battleMapStore.setMessage("Salvando alinhamento do grid...");
  void new HttpClient()
    .submitGridCalibration(sessionId, {
      actionId,
      sessionId,
      gridCalibration,
      gridWidth,
      gridHeight,
      knownVersion: battleMapStore.getEncounter()?.combatState.version ?? 0
    })
    .catch(() => {
      battleMapStore.failGridCalibrationUpdate(actionId);
      battleMapStore.setMessage("Nao foi possivel salvar o grid. Tente novamente.");
    });
}
