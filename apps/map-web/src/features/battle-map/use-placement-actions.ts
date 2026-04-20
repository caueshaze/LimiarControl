import type { Coordinate } from "@limiarmap/shared-contracts";
import { HttpClient } from "../../services/http-client";
import { battleMapStore } from "./battle-map-store";

export function submitPlacement(sessionId: string, tokenId: string, position: Coordinate): void {
  void new HttpClient()
    .submitPlacement(sessionId, {
      actionId: `place:${tokenId}:${Date.now()}`,
      tokenId,
      position,
    })
    .catch(() => {
      battleMapStore.setMessage("Nao foi possivel posicionar o token.");
    });
}
