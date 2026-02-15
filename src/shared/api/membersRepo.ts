import type { RoleMode } from "../types/role";
import { http } from "./http";

type MemberProfile = {
  campaignId: string;
  displayName: string;
  roleMode: RoleMode;
};

type MemberSummary = {
  id: string;
  displayName: string;
  roleMode: RoleMode;
};

export const membersRepo = {
  getMe: (campaignId: string) =>
    http.get<MemberProfile>(`/campaigns/${campaignId}/members/me`),
  list: (campaignId: string) =>
    http.get<MemberSummary[]>(`/campaigns/${campaignId}/members`),
  updateRole: (
    campaignId: string,
    payload: { roleMode: RoleMode }
  ) =>
    http.patch<MemberProfile>(`/campaigns/${campaignId}/members/me`, {
      role: payload.roleMode,
    }),
};
