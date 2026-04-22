import type { Coordinate } from "@limiarmap/shared-contracts";
import { HttpClient } from "../../services/http-client";
import { setTargetingPreview } from "./targeting-preview-store";
import { battleMapStore } from "../battle-map/battle-map-store";

export function previewTargeting(cells: Coordinate[]): void {
  setTargetingPreview(cells);
}

export function submitTargeting(
  sessionId: string,
  tokenId: string,
  shape: "line" | "cone" | "sphere" | "cube" | "cylinder",
  originCell: Coordinate,
  anchorCell: Coordinate,
  rangeCells: number,
  sizeCells: number
): void {
  if (battleMapStore.getState().isGridEditMode) {
    battleMapStore.setMessage("Saia do modo de edicao do grid antes de usar targeting.");
    return;
  }

  if (battleMapStore.getState().isObstaclePaintMode) {
    battleMapStore.setMessage("Saia do modo de obstaculos antes de usar targeting.");
    return;
  }

  void new HttpClient()
    .submitTargeting(sessionId, {
      actionId: `target:${Date.now()}`,
      sessionId,
      tokenId,
      shape,
      originCell,
      anchorCell,
      rangeCells,
      sizeCells,
      knownVersion: battleMapStore.getEncounter()?.combatState.version ?? 0,
      requiresSight: false,
      requiresEffect: false
    })
    .catch(() => {
      battleMapStore.setTargetingPreview([]);
      battleMapStore.setMessage("Nao foi possivel enviar o targeting. Tente novamente.");
    });
}
