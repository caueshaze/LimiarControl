export const CampaignSystemType = {
  DND5E: "DND5E",
  T20: "T20",
  PF2E: "PF2E",
  COC: "COC",
  CUSTOM: "CUSTOM",
} as const;

export type CampaignSystemType =
  (typeof CampaignSystemType)[keyof typeof CampaignSystemType];

export const campaignSystemLabels: Record<CampaignSystemType, string> = {
  DND5E: "D&D 5e",
  T20: "Tormenta20",
  PF2E: "Pathfinder 2e",
  COC: "Call of Cthulhu",
  CUSTOM: "Custom",
};

export const getCampaignSystemLabel = (systemType: CampaignSystemType) =>
  campaignSystemLabels[systemType];

export const defaultCampaignSystemType = CampaignSystemType.DND5E;

export const enabledCampaignSystemTypes = [
  CampaignSystemType.DND5E,
] as const satisfies readonly CampaignSystemType[];

export const isCampaignSystemEnabled = (systemType: CampaignSystemType) =>
  (enabledCampaignSystemTypes as readonly CampaignSystemType[]).includes(systemType);

export const enabledCampaignSystemOptions = enabledCampaignSystemTypes.map(
  (systemType) => ({
    value: systemType,
    label: campaignSystemLabels[systemType],
  }),
);

export type Campaign = {
  id: string;
  name: string;
  systemType: CampaignSystemType;
  roleMode?: "GM" | "PLAYER";
  createdAt: string;
  updatedAt?: string | null;
};

export type CampaignMapCalibration = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type BlockedCell = {
  x: number;
  y: number;
};

export type ObstacleCover = "none" | "half" | "threeQuarters" | "full";

export type CampaignObstacle = {
  x: number;
  y: number;
  blocksMovement: boolean;
  blocksEffect: boolean;
  blocksVision: boolean;
  cover: ObstacleCover;
  clipsDiagonalMovement: boolean;
  movementCostMultiplier: number;
};

export type CampaignEdgeDirection = "N" | "E" | "S" | "W";

export type CampaignEdgeObstacle = {
  x: number;
  y: number;
  direction: CampaignEdgeDirection;
  blocksMovement: boolean;
  blocksVision: boolean;
  blocksEffect: boolean;
  cover: ObstacleCover;
};

export type CampaignCellElevation = {
  x: number;
  y: number;
  elevationMeters: number;
};

export type ObstaclePresetId =
  | "solid_wall"
  | "dense_obstacle"
  | "barricade"
  | "transparent_barrier"
  | "blocked_path"
  | "spell_blocker"
  | "difficult_terrain";

export type ObstaclePreset = {
  id: ObstaclePresetId;
  label: string;
  description: string;
  /** Hex color for visual overlay on the map preview. */
  color: string;
  style: Omit<CampaignObstacle, "x" | "y">;
};

export type EdgeObstaclePresetId =
  | "edge_wall"
  | "edge_barrier"
  | "edge_cover_half"
  | "edge_cover_three_quarters"
  | "edge_vision_blocker"
  | "edge_effect_blocker";

export type EdgeObstaclePreset = {
  id: EdgeObstaclePresetId;
  label: string;
  description: string;
  color: string;
  style: Omit<CampaignEdgeObstacle, "x" | "y" | "direction">;
};

export const CAMPAIGN_OBSTACLE_PRESETS: ObstaclePreset[] = [
  {
    id: "solid_wall",
    label: "Parede sólida",
    description: "Bloqueia movimento, visão e efeito; cobertura total.",
    color: "#d24646",
    style: { blocksMovement: true, blocksEffect: true, blocksVision: true, cover: "full", clipsDiagonalMovement: true, movementCostMultiplier: 1 },
  },
  {
    id: "dense_obstacle",
    label: "Obstáculo denso",
    description: "Bloqueia movimento e concede 3/4 de cobertura. Não bloqueia visão nem efeito.",
    color: "#ffaa44",
    style: { blocksMovement: true, blocksEffect: false, blocksVision: false, cover: "threeQuarters", clipsDiagonalMovement: true, movementCostMultiplier: 1 },
  },
  {
    id: "barricade",
    label: "Barricada",
    description: "Meia cobertura. Não bloqueia movimento, visão nem efeito.",
    color: "#ffdc78",
    style: { blocksMovement: false, blocksEffect: false, blocksVision: false, cover: "half", clipsDiagonalMovement: false, movementCostMultiplier: 1 },
  },
  {
    id: "transparent_barrier",
    label: "Barreira transparente",
    description: "Bloqueia movimento e efeito, mas não bloqueia visão.",
    color: "#7c9ef5",
    style: { blocksMovement: true, blocksEffect: true, blocksVision: false, cover: "none", clipsDiagonalMovement: false, movementCostMultiplier: 1 },
  },
  {
    id: "blocked_path",
    label: "Caminho bloqueado",
    description: "Bloqueia movimento sem bloquear visão, efeito ou oferecer cobertura.",
    color: "#c084fc",
    style: { blocksMovement: true, blocksEffect: false, blocksVision: false, cover: "none", clipsDiagonalMovement: false, movementCostMultiplier: 1 },
  },
  {
    id: "spell_blocker",
    label: "Bloqueador de magia",
    description: "Bloqueia efeito de área sem bloquear movimento ou visão.",
    color: "#34d399",
    style: { blocksMovement: false, blocksEffect: true, blocksVision: false, cover: "none", clipsDiagonalMovement: false, movementCostMultiplier: 1 },
  },
  {
    id: "difficult_terrain",
    label: "Terreno difícil",
    description: "Não bloqueia, mas custa 2× para atravessar.",
    color: "#9c7040",
    style: { blocksMovement: false, blocksEffect: false, blocksVision: false, cover: "none", clipsDiagonalMovement: false, movementCostMultiplier: 2 },
  },
];

export const CAMPAIGN_EDGE_OBSTACLE_PRESETS: EdgeObstaclePreset[] = [
  {
    id: "edge_wall",
    label: "Parede (borda)",
    description: "Bloqueia movimento, visao e efeito na borda entre celulas.",
    color: "#d24646",
    style: {
      blocksMovement: true,
      blocksVision: true,
      blocksEffect: true,
      cover: "full",
    },
  },
  {
    id: "edge_barrier",
    label: "Barreira (borda)",
    description: "Bloqueia movimento, mas permite visao e efeito.",
    color: "#ffa436",
    style: {
      blocksMovement: true,
      blocksVision: false,
      blocksEffect: false,
      cover: "none",
    },
  },
  {
    id: "edge_cover_half",
    label: "Cobertura 1/2 (borda)",
    description: "Concede meia cobertura na borda sem bloquear passagem.",
    color: "#ffdc78",
    style: {
      blocksMovement: false,
      blocksVision: false,
      blocksEffect: false,
      cover: "half",
    },
  },
  {
    id: "edge_cover_three_quarters",
    label: "Cobertura 3/4 (borda)",
    description: "Concede cobertura de tres quartos na borda.",
    color: "#ffaa44",
    style: {
      blocksMovement: false,
      blocksVision: false,
      blocksEffect: false,
      cover: "threeQuarters",
    },
  },
  {
    id: "edge_vision_blocker",
    label: "Barreira visual (borda)",
    description: "Bloqueia visao sem bloquear movimento ou efeito.",
    color: "#5ed2ff",
    style: {
      blocksMovement: false,
      blocksVision: true,
      blocksEffect: false,
      cover: "none",
    },
  },
  {
    id: "edge_effect_blocker",
    label: "Barreira de efeito (borda)",
    description: "Bloqueia efeito sem bloquear movimento ou visao.",
    color: "#bc56ff",
    style: {
      blocksMovement: false,
      blocksVision: false,
      blocksEffect: true,
      cover: "none",
    },
  },
];

export function obstacleToPresetId(obs: CampaignObstacle): ObstaclePresetId {
  for (const preset of CAMPAIGN_OBSTACLE_PRESETS) {
    const s = preset.style;
    if (
      s.blocksMovement === obs.blocksMovement &&
      s.blocksEffect === obs.blocksEffect &&
      s.blocksVision === obs.blocksVision &&
      s.cover === obs.cover &&
      s.clipsDiagonalMovement === obs.clipsDiagonalMovement &&
      s.movementCostMultiplier === obs.movementCostMultiplier
    ) {
      return preset.id;
    }
  }
  return "solid_wall";
}

export function edgeObstacleToPresetId(
  obstacle: CampaignEdgeObstacle,
): EdgeObstaclePresetId {
  for (const preset of CAMPAIGN_EDGE_OBSTACLE_PRESETS) {
    const style = preset.style;
    if (
      style.blocksMovement === obstacle.blocksMovement &&
      style.blocksVision === obstacle.blocksVision &&
      style.blocksEffect === obstacle.blocksEffect &&
      style.cover === obstacle.cover
    ) {
      return preset.id;
    }
  }
  return "edge_wall";
}

export type CampaignMapConfig = {
  id: string;
  mapName?: string | null;
  imageUrl?: string | null;
  gridWidth?: number | null;
  gridHeight?: number | null;
  calibration?: CampaignMapCalibration | null;
  /** Canonical semantic obstacles. Null = legacy map without obstacles_json. */
  obstacles?: CampaignObstacle[] | null;
  /** Canonical semantic edge obstacles authored between adjacent cells. */
  edgeObstacles?: CampaignEdgeObstacle[] | null;
  /** Per-cell elevation metadata for fall detection. */
  cellElevations?: CampaignCellElevation[] | null;
  /** @deprecated Legacy movement-only blocked cells for pre-semantic maps. */
  blockedCells?: BlockedCell[] | null;
  createdAt: string;
  updatedAt?: string | null;
};
