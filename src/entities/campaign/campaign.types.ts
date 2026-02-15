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

export type Campaign = {
  id: string;
  name: string;
  systemType: CampaignSystemType;
  createdAt: string;
};
