import type { Coordinate } from "@limiarmap/shared-contracts";
import { HttpClient } from "../../services/http-client";
import { battleMapStore } from "./battle-map-store";

export function submitMovement(sessionId: string, tokenId: string, path: Coordinate[]): void {
  if (battleMapStore.getState().isGridEditMode) {
    battleMapStore.setMessage("Saia do modo de edicao do grid antes de mover tokens.");
    return;
  }

  if (battleMapStore.getState().isObstaclePaintMode) {
    battleMapStore.setMessage("Saia do modo de obstaculos antes de mover tokens.");
    return;
  }

  battleMapStore.setMovementPreview(path);
  void new HttpClient()
    .submitMovement(sessionId, {
      actionId: `move:${Date.now()}`,
      sessionId,
      tokenId,
      path,
      knownVersion: battleMapStore.getEncounter()?.combatState.version ?? 0
    })
    .catch(() => {
      battleMapStore.setMovementPreview([]);
      battleMapStore.setMessage("Nao foi possivel enviar o movimento. Tente novamente.");
    });
}
