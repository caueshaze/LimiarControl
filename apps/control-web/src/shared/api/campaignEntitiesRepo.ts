import type { CampaignEntity, CampaignEntityPayload, CampaignEntityPublic } from "../../entities/campaign-entity";
import { http } from "./http";

export const campaignEntitiesRepo = {
  list: (campaignId: string) =>
    http.get<CampaignEntity[]>(`/campaigns/${campaignId}/entities`),

  listPublic: (campaignId: string) =>
    http.get<CampaignEntityPublic[]>(`/campaigns/${campaignId}/entities/public`),

  create: (campaignId: string, payload: CampaignEntityPayload) =>
    http.post<CampaignEntity>(`/campaigns/${campaignId}/entities`, payload),

  update: (campaignId: string, entityId: string, payload: CampaignEntityPayload) =>
    http.put<CampaignEntity>(`/campaigns/${campaignId}/entities/${entityId}`, payload),

  remove: (campaignId: string, entityId: string) =>
    http.del<void>(`/campaigns/${campaignId}/entities/${entityId}`),
};
