export type CharacterSheetRecord = {
  id: string;
  playerId: string;
  partyId: string;
  data: unknown; // JSON blob — validado pelo Zod no frontend ao carregar
  sourceDraftId?: string | null;
  deliveredByUserId?: string | null;
  deliveredAt?: string | null;
  acceptedAt?: string | null;
  createdAt: string;
  updatedAt?: string | null;
};

export type PartyCharacterSheetDraftRecord = {
  id: string;
  partyId: string;
  name: string;
  data: unknown;
  status: "active" | "archived";
  createdByUserId: string;
  archivedAt?: string | null;
  lastDerivedAt?: string | null;
  createdAt: string;
  updatedAt?: string | null;
};

export type SessionStateRecord = {
  id: string;
  sessionId: string;
  playerUserId: string;
  state: unknown;
  createdAt: string;
  updatedAt?: string | null;
};
