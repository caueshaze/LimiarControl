import type { RoleMode } from "../types/role";
import { http } from "./http";

type RoleModeResponse = { roleMode: RoleMode };

export const roleModeRepo = {
  get: (campaignId: string) =>
    http.get<RoleModeResponse>(`/campaigns/${campaignId}/role-mode`),
  update: (campaignId: string, roleMode: RoleMode) =>
    http.put<RoleModeResponse>(`/campaigns/${campaignId}/role-mode`, { roleMode }),
};
