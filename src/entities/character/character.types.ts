export type CharacterSheetRecord = {
  id: string;
  playerId: string;
  partyId: string;
  data: unknown; // JSON blob — validado pelo Zod no frontend ao carregar
  createdAt: string;
  updatedAt: string;
};

export type SessionStateRecord = {
  id: string;
  sessionId: string;
  playerUserId: string;
  state: unknown;
  createdAt: string;
  updatedAt?: string | null;
};
