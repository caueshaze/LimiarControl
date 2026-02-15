import type { Campaign, CampaignSystemType } from "../../entities/campaign";
import { http } from "./http";

type CampaignCreatePayload = {
  name: string;
  system: CampaignSystemType;
};

export type CampaignOverview = {
  id: string;
  name: string;
  joinCode?: string | null;
  systemType: CampaignSystemType;
  roleMode: "GM" | "PLAYER";
  createdAt: string;
  updatedAt?: string | null;
  gmName?: string | null;
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
  joinByCode: (payload: { joinCode: string }) =>
    http.post<{
      campaignId: string;
      campaignName: string;
      gmName?: string | null;
      memberId: string;
      displayName: string;
      roleMode: "GM" | "PLAYER";
    }>(`/campaigns/join-by-code`, payload),
};
