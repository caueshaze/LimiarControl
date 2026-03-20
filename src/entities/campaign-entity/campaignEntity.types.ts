export type EntityCategory = "npc" | "enemy" | "creature" | "ally";

export type AbilityStats = {
  str?: number | null;
  dex?: number | null;
  con?: number | null;
  int?: number | null;
  wis?: number | null;
  cha?: number | null;
};

export type CampaignEntity = {
  id: string;
  campaignId: string;
  name: string;
  category: EntityCategory;
  description?: string | null;
  imageUrl?: string | null;
  baseHp?: number | null;
  baseAc?: number | null;
  stats?: AbilityStats | null;
  actions?: string | null;
  notesPrivate?: string | null;
  notesPublic?: string | null;
  createdAt: string;
  updatedAt?: string | null;
};

export type CampaignEntityPublic = Omit<CampaignEntity, "notesPrivate">;

export type CampaignEntityPayload = Omit<CampaignEntity, "id" | "campaignId" | "createdAt" | "updatedAt">;
