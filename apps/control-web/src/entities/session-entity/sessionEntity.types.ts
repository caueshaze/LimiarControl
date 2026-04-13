import type { CampaignEntity, CampaignEntityPublic } from "../campaign-entity";

export type SessionEntity = {
  id: string;
  sessionId: string;
  campaignEntityId: string;
  visibleToPlayers: boolean;
  currentHp?: number | null;
  overrides?: Record<string, unknown> | null;
  label?: string | null;
  revealedAt?: string | null;
  createdAt: string;
  updatedAt?: string | null;
  entity?: CampaignEntity | null;
};

export type SessionEntityPlayer = {
  id: string;
  sessionId: string;
  campaignEntityId: string;
  currentHp?: number | null;
  label?: string | null;
  revealedAt?: string | null;
  entity?: CampaignEntityPublic | null;
};

export type SessionEntityCreatePayload = {
  campaignEntityId: string;
  label?: string | null;
  currentHp?: number | null;
};

export type SessionEntityUpdatePayload = {
  visibleToPlayers?: boolean | null;
  currentHp?: number | null;
  label?: string | null;
  overrides?: Record<string, unknown> | null;
};
