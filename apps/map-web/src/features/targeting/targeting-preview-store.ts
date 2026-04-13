import type { Coordinate } from "@limiarmap/shared-contracts";
import { battleMapStore } from "../battle-map/battle-map-store";

export function setTargetingPreview(cells: Coordinate[]): void {
  battleMapStore.setTargetingPreview(cells);
}
