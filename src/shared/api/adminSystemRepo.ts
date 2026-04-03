import type {
  AdminCampaign,
  AdminCampaignFilters,
  AdminDiagnostics,
  AdminOverview,
  AdminUser,
  AdminUserFilters,
  AdminUserUpdatePayload,
} from "../../entities/admin-system";
import { http } from "./http";

const toUserQueryString = (filters?: AdminUserFilters) => {
  if (!filters) {
    return "";
  }

  const params = new URLSearchParams();
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (filters.role) {
    params.set("role", filters.role);
  }
  if (typeof filters.isSystemAdmin === "boolean") {
    params.set("is_system_admin", String(filters.isSystemAdmin));
  }
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
};

const toCampaignQueryString = (filters?: AdminCampaignFilters) => {
  if (!filters) {
    return "";
  }

  const params = new URLSearchParams();
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (filters.system) {
    params.set("system", filters.system);
  }
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
};

export const adminSystemRepo = {
  overview: () => http.get<AdminOverview>("/admin/overview"),
  listUsers: (filters?: AdminUserFilters) =>
    http.get<AdminUser[]>(`/admin/users${toUserQueryString(filters)}`),
  updateUser: (userId: string, payload: AdminUserUpdatePayload) =>
    http.patch<AdminUser>(`/admin/users/${userId}`, payload),
  deleteUser: (userId: string) => http.del(`/admin/users/${userId}`),
  listCampaigns: (filters?: AdminCampaignFilters) =>
    http.get<AdminCampaign[]>(`/admin/campaigns${toCampaignQueryString(filters)}`),
  deleteCampaign: (campaignId: string) => http.del(`/admin/campaigns/${campaignId}`),
  diagnostics: () => http.get<AdminDiagnostics>("/admin/diagnostics"),
};
