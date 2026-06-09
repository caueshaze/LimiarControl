import type { RoleMode } from "../types/role";

const LEGACY_MODE_KEY = "limiar_experience_mode";
const LEGACY_MODE_OWNER_KEY = "limiar_experience_mode_owner";

const isRoleMode = (value: unknown): value is RoleMode =>
  value === "GM" || value === "PLAYER";

export const workspaceModeStorage = {
  legacyModeKey: LEGACY_MODE_KEY,
  legacyModeOwnerKey: LEGACY_MODE_OWNER_KEY,
  readLegacyMode(currentUserId?: string | null): RoleMode | null {
    if (typeof window === "undefined") {
      return null;
    }
    const stored = window.localStorage.getItem(LEGACY_MODE_KEY);
    if (!isRoleMode(stored)) {
      return null;
    }
    const ownerId = window.localStorage.getItem(LEGACY_MODE_OWNER_KEY);
    if (ownerId && currentUserId && ownerId !== currentUserId) {
      return null;
    }
    return stored;
  },
  writeLegacyMode(mode: RoleMode, ownerUserId?: string | null) {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(LEGACY_MODE_KEY, mode);
    if (ownerUserId) {
      window.localStorage.setItem(LEGACY_MODE_OWNER_KEY, ownerUserId);
    } else {
      window.localStorage.removeItem(LEGACY_MODE_OWNER_KEY);
    }
  },
  clearLegacyMode() {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.removeItem(LEGACY_MODE_KEY);
    window.localStorage.removeItem(LEGACY_MODE_OWNER_KEY);
  },
};

export function resolveEffectiveWorkspaceMode(params: {
  preferredWorkspaceMode?: RoleMode | null;
  legacyWorkspaceMode?: RoleMode | null;
  hasGmCampaign: boolean;
}): RoleMode {
  if (params.preferredWorkspaceMode) {
    return params.preferredWorkspaceMode;
  }
  if (params.legacyWorkspaceMode) {
    return params.legacyWorkspaceMode;
  }
  return params.hasGmCampaign ? "GM" : "PLAYER";
}

export function getWorkspaceModeButtonOrder(mode: RoleMode): [RoleMode, RoleMode] {
  return mode === "PLAYER" ? ["PLAYER", "GM"] : ["GM", "PLAYER"];
}
