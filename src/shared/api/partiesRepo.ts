import { http } from "./http";

export type PartySummary = {
  id: string;
  campaignId: string;
  gmUserId: string;
  name: string;
  createdAt: string;
};

export type PartyMemberSummary = {
  userId: string;
  role: "GM" | "PLAYER";
  status: "invited" | "joined" | "declined" | "left";
  createdAt: string;
  displayName?: string | null;
  username?: string | null;
};

export type PartyDetail = PartySummary & {
  members: PartyMemberSummary[];
};

export type PartyActiveSession = {
  id: string;
  campaignId: string;
  partyId?: string | null;
  number: number;
  title: string;

  status: "LOBBY" | "ACTIVE" | "CLOSED";
  isActive: boolean;
  startedAt?: string | null;
  endedAt?: string | null;
  durationSeconds: number;
  createdAt: string;
  updatedAt?: string | null;
};

export type PartyInvite = {
  party: PartySummary;
  campaignName: string;
  status: "invited";
  activeSession?: PartyActiveSession | null;
};

export const partiesRepo = {
  listMine: () => http.get<PartySummary[]>("/me/parties"),
  listInvites: () => http.get<PartyInvite[]>("/me/party-invites"),
  create: (payload: { campaignId: string; name: string; playerIds?: string[] }) =>
    http.post<PartySummary>("/parties", payload),
  get: (partyId: string) => http.get<PartyDetail>(`/parties/${partyId}`),
  addMember: (
    partyId: string,
    payload: { userId: string; role: "GM" | "PLAYER"; status?: "invited" | "joined" | "declined" | "left" }
  ) => http.post<PartyMemberSummary>(`/parties/${partyId}/members`, payload),
  getMyMember: (partyId: string) =>
    http.get<PartyMemberSummary>(`/parties/${partyId}/members/me`),
  joinInvite: (partyId: string) =>
    http.post<PartyMemberSummary>(`/parties/${partyId}/members/me/join`, {}),
  declineInvite: (partyId: string) =>
    http.post<PartyMemberSummary>(`/parties/${partyId}/members/me/decline`, {}),
  leave: (partyId: string) =>
    http.post<PartyMemberSummary>(`/parties/${partyId}/members/me/leave`, {}),
  listPartySessions: (partyId: string) =>
    http.get<PartyActiveSession[]>(`/parties/${partyId}/sessions`),
  getPartyActiveSession: (partyId: string) =>
    http.get<PartyActiveSession>(`/parties/${partyId}/sessions/active`),
  createPartySession: (partyId: string, payload: { title: string }) =>
    http.post<PartyActiveSession>(`/parties/${partyId}/sessions`, payload),
  closePartySession: (partyId: string, sessionId: string) =>
    http.post<PartyActiveSession>(`/parties/${partyId}/sessions/${sessionId}/close`, {}),
};
