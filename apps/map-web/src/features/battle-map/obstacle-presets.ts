/**
 * Obstacle brush presets — Phase 6 + Phase 7.
 *
 * Presets are authoring conveniences only. The obstacle mechanics always rely
 * on the explicit semantic fields (blocksMovement, blocksEffect, blocksVision,
 * cover, clipsDiagonalMovement, movementCostMultiplier). Preset IDs are never
 * persisted to the server.
 *
 * Preset set (7 tactically distinct choices):
 *
 * | ID                  | Mv | Fx | Vi | Cover        | Cost | Use case                         |
 * |---------------------|----|----|-----|--------------|------|----------------------------------|
 * | solid_wall          | ✓  | ✓  | ✓  | full         |  —   | Stone wall, rock face             |
 * | dense_obstacle      | ✓  | ✗  | ✗  | threeQuarters|  —   | Boulder, pillar, heavy furniture  |
 * | barricade           | ✗  | ✗  | ✗  | half         |  1×  | Sandbags, low wall, chest-high    |
 * | transparent_barrier | ✓  | ✓  | ✗  | none         |  —   | Force wall, glass pane            |
 * | blocked_path        | ✓  | ✗  | ✗  | none         |  —   | Door, fence, shallow crossing     |
 * | spell_blocker       | ✗  | ✓  | ✗  | none         |  1×  | Magical ward, anti-magic zone     |
 * | difficult_terrain   | ✗  | ✗  | ✗  | none         |  2×  | Swamp, rubble, flooded area       |
 */
import type { ObstacleStyle } from "@limiarmap/shared-contracts";

export type ObstacleBrushPresetId =
  | "solid_wall"
  | "dense_obstacle"
  | "barricade"
  | "transparent_barrier"
  | "blocked_path"
  | "spell_blocker"
  | "difficult_terrain";

export type EdgeBrushPresetId =
  | "edge_wall"
  | "edge_barrier"
  | "edge_cover_half"
  | "edge_cover_three_quarters"
  | "edge_vision_blocker"
  | "edge_effect_blocker";

export interface ObstacleBrushPreset {
  id: ObstacleBrushPresetId;
  label: string;
  description: string;
  /** Map canvas color hex for display in the preset selector swatch. */
  swatchColor: string;
  status: "active" | "prepared";
  style: ObstacleStyle;
}

export const OBSTACLE_BRUSH_PRESETS: ObstacleBrushPreset[] = [
  {
    id: "solid_wall",
    label: "Parede solida",
    description:
      "Bloqueia movimento, visao e efeito; cobertura total. Paredes, rochas, obstaculos impenetraveis.",
    swatchColor: "#d24646",
    status: "active",
    style: {
      blocksMovement: true,
      blocksEffect: true,
      blocksVision: true,
      cover: "full",
      clipsDiagonalMovement: true,
      movementCostMultiplier: 1
    }
  },
  {
    id: "dense_obstacle",
    label: "Obstaculo denso",
    description:
      "Bloqueia movimento e concede cobertura de tres quartos (+5 AC). Nao bloqueia visao nem efeito. Pilares, pedras, moveis pesados.",
    swatchColor: "#ffaa44",
    status: "active",
    style: {
      blocksMovement: true,
      blocksEffect: false,
      blocksVision: false,
      cover: "threeQuarters",
      clipsDiagonalMovement: true,
      movementCostMultiplier: 1
    }
  },
  {
    id: "barricade",
    label: "Barricada",
    description:
      "Concede meia cobertura (+2 AC). Nao bloqueia movimento, visao nem efeito. Sacos de areia, muros baixos, cobertura parcial.",
    swatchColor: "#ffdc78",
    status: "active",
    style: {
      blocksMovement: false,
      blocksEffect: false,
      blocksVision: false,
      cover: "half",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    }
  },
  {
    id: "transparent_barrier",
    label: "Barreira transparente",
    description:
      "Bloqueia movimento e efeito, mas nao bloqueia visao. Paredes de forca, vidro magico, barreiras elemental.",
    swatchColor: "#d24646",
    status: "active",
    style: {
      blocksMovement: true,
      blocksEffect: true,
      blocksVision: false,
      cover: "none",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    }
  },
  {
    id: "difficult_terrain",
    label: "Terreno dificil",
    description:
      "Nao bloqueia movimento, mas custa o dobro para atravessar (2× custo por celula). Pantano, escombros, area inundada, neve profunda.",
    swatchColor: "#9c7040",
    status: "active",
    style: {
      blocksMovement: false,
      blocksEffect: false,
      blocksVision: false,
      cover: "none",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 2
    }
  }
];

export interface EdgeBrushPreset {
  id: EdgeBrushPresetId;
  label: string;
  description: string;
  swatchColor: string;
  style: ObstacleStyle;
}

export const EDGE_BRUSH_PRESETS: EdgeBrushPreset[] = [
  {
    id: "edge_wall",
    label: "Parede (borda)",
    description:
      "Bloqueia movimento, visao e efeito na borda entre celulas. Paredes finas entre adjacentes.",
    swatchColor: "#d24646",
    style: {
      blocksMovement: true,
      blocksEffect: true,
      blocksVision: true,
      cover: "full",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    }
  },
  {
    id: "edge_barrier",
    label: "Barreira (borda)",
    description:
      "Bloqueia movimento mas permite visao e efeito. Portas, grades, cancelas.",
    swatchColor: "#ffa436",
    style: {
      blocksMovement: true,
      blocksEffect: false,
      blocksVision: false,
      cover: "none",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    }
  },
  {
    id: "edge_cover_half",
    label: "Cobertura 1/2 (borda)",
    description:
      "Meia cobertura na borda. Muros baixos, barricadas entre celulas.",
    swatchColor: "#ffdc78",
    style: {
      blocksMovement: false,
      blocksEffect: false,
      blocksVision: false,
      cover: "half",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    }
  },
  {
    id: "edge_cover_three_quarters",
    label: "Cobertura 3/4 (borda)",
    description:
      "Cobertura de tres quartos na borda. Parapeitos altos, muros medianos.",
    swatchColor: "#ffaa44",
    style: {
      blocksMovement: false,
      blocksEffect: false,
      blocksVision: false,
      cover: "threeQuarters",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    }
  },
  {
    id: "edge_vision_blocker",
    label: "Barreira visual (borda)",
    description:
      "Bloqueia visao sem bloquear movimento ou efeito. Fumaca, ilusoes.",
    swatchColor: "#5ed2ff",
    style: {
      blocksMovement: false,
      blocksEffect: false,
      blocksVision: true,
      cover: "none",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    }
  },
  {
    id: "edge_effect_blocker",
    label: "Barreira de efeito (borda)",
    description:
      "Bloqueia efeito sem bloquear movimento ou visao. Campos anti-magia.",
    swatchColor: "#bc56ff",
    style: {
      blocksMovement: false,
      blocksEffect: true,
      blocksVision: false,
      cover: "none",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    }
  }
];

export function getObstacleBrushPreset(
  presetId: ObstacleBrushPresetId
): ObstacleBrushPreset {
  return (
    OBSTACLE_BRUSH_PRESETS.find((preset) => preset.id === presetId) ??
    OBSTACLE_BRUSH_PRESETS[0]
  );
}

export function getEdgeBrushPreset(
  presetId: EdgeBrushPresetId
): EdgeBrushPreset {
  return (
    EDGE_BRUSH_PRESETS.find((preset) => preset.id === presetId) ??
    EDGE_BRUSH_PRESETS[0]
  );
}
