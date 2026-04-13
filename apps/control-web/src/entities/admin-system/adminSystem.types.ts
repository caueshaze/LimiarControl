import type { CampaignSystemType } from "../campaign";
import type { RoleMode } from "../../shared/types/role";

export type AdminOverview = {
  usersTotal: number;
  systemAdminsTotal: number;
  campaignsTotal: number;
  partiesTotal: number;
  sessionsTotal: number;
  activeSessionsTotal: number;
  baseItemsActive: number;
  baseItemsInactive: number;
  baseSpellsActive: number;
  baseSpellsInactive: number;
};

export type AdminUser = {
  id: string;
  username: string;
  displayName: string;
  role: RoleMode;
  isSystemAdmin: boolean;
  campaignsCount: number;
  gmCampaignsCount: number;
  partiesCount: number;
  createdAt: string;
  updatedAt?: string | null;
};

export type AdminUserFilters = {
  search?: string;
  role?: RoleMode;
  isSystemAdmin?: boolean;
  limit?: number;
};

export type AdminUserUpdatePayload = {
  role?: RoleMode;
  isSystemAdmin?: boolean;
};

export type AdminCampaign = {
  id: string;
  name: string;
  systemType: CampaignSystemType;
  roleMode: RoleMode;
  gmNames: string[];
  membersCount: number;
  partiesCount: number;
  sessionsCount: number;
  activeSessionsCount: number;
  itemCatalogSnapshotAt?: string | null;
  spellCatalogSnapshotAt?: string | null;
  createdAt: string;
  updatedAt?: string | null;
};

export type AdminCampaignFilters = {
  search?: string;
  system?: CampaignSystemType;
  limit?: number;
};

export type AdminDiagnostics = {
  appEnv: string;
  autoMigrate: boolean;
  utcNow: string;
  databaseOk: boolean;
  databaseMessage?: string | null;
  usersTotal: number;
  campaignsTotal: number;
  partiesTotal: number;
  sessionsTotal: number;
  activeSessionsTotal: number;
  activeCombatsTotal: number;
};
