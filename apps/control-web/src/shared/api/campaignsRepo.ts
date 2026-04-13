import type { BlockedCell, Campaign, CampaignMapConfig, CampaignSystemType } from "../../entities/campaign";
import { http } from "./http";

type CampaignCreatePayload = {
  name: string;
  system: CampaignSystemType;
};

export type CampaignOverview = {
  id: string;
  name: string;
  systemType: CampaignSystemType;
  roleMode: "GM" | "PLAYER";
  createdAt: string;
  updatedAt?: string | null;
  gmName?: string | null;
  maps: CampaignMapConfig[];
};

export type CampaignMapConfigPayload = {
  mapName?: string | null;
  imageUrl?: string | null;
  gridWidth?: number | null;
  gridHeight?: number | null;
  calibration?: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
  /** Pass an array to replace blocked cells; omit to leave them unchanged. */
  blockedCells?: BlockedCell[] | null;
};

export const campaignsRepo = {
  list: () => http.get<Campaign[]>("/me/campaigns"),
  create: (payload: CampaignCreatePayload) =>
    http.post<Campaign>("/campaigns", payload),
  update: (campaignId: string, payload: CampaignCreatePayload) =>
    http.put<Campaign>(`/campaigns/${campaignId}`, payload),
  remove: (campaignId: string) => http.del<void>(`/campaigns/${campaignId}`),
  overview: (campaignId: string) =>
    http.get<CampaignOverview>(`/campaigns/${campaignId}/overview`),
  listMaps: (campaignId: string) =>
    http.get<CampaignMapConfig[]>(`/campaigns/${campaignId}/maps`),
  createMap: (campaignId: string, payload: CampaignMapConfigPayload) =>
    http.post<CampaignMapConfig>(`/campaigns/${campaignId}/maps`, payload),
  updateMap: (campaignId: string, mapId: string, payload: CampaignMapConfigPayload) =>
    http.put<CampaignMapConfig>(`/campaigns/${campaignId}/maps/${mapId}`, payload),
  deleteMap: (campaignId: string, mapId: string) =>
    http.del<void>(`/campaigns/${campaignId}/maps/${mapId}`),
};
