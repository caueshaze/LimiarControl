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

export type CampaignMapConfig = {
  id: string;
  mapName?: string | null;
  imageUrl?: string | null;
  gridWidth?: number | null;
  gridHeight?: number | null;
  calibration?: CampaignMapCalibration | null;
  /** Movement-blocking cells defined at the campaign map level (Phase 1 obstacles). */
  blockedCells?: BlockedCell[] | null;
  createdAt: string;
  updatedAt?: string | null;
};
