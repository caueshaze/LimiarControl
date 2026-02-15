import type { NPC } from "../../entities/npc";
import { http } from "./http";

type NpcPayload = Omit<NPC, "id" | "createdAt" | "updatedAt" | "campaignId">;

export const npcsRepo = {
  list: (campaignId: string) => http.get<NPC[]>(`/campaigns/${campaignId}/npcs`),
  create: (campaignId: string, payload: NpcPayload) =>
    http.post<NPC>(`/campaigns/${campaignId}/npcs`, payload),
  update: (campaignId: string, npcId: string, payload: NpcPayload) =>
    http.put<NPC>(`/campaigns/${campaignId}/npcs/${npcId}`, payload),
  remove: (campaignId: string, npcId: string) =>
    http.del<void>(`/campaigns/${campaignId}/npcs/${npcId}`),
};
