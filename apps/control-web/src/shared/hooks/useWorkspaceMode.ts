import { useEffect, useMemo } from "react";
import { useAuth } from "../../features/auth";
import { useCampaigns } from "../../features/campaign-select";
import {
  resolveEffectiveWorkspaceMode,
  workspaceModeStorage,
} from "../lib/workspaceMode";
import type { RoleMode } from "../types/role";

export const useWorkspaceMode = () => {
  const { user, updateProfile } = useAuth();
  const { campaigns } = useCampaigns();

  const hasGmCampaign = useMemo(
    () => campaigns.some((campaign) => campaign.roleMode === "GM"),
    [campaigns],
  );
  const legacyWorkspaceMode = useMemo(
    () => workspaceModeStorage.readLegacyMode(user?.userId),
    [user?.userId],
  );

  const mode = useMemo(
    () =>
      resolveEffectiveWorkspaceMode({
        preferredWorkspaceMode: user?.preferredWorkspaceMode ?? null,
        legacyWorkspaceMode,
        hasGmCampaign,
      }),
    [hasGmCampaign, legacyWorkspaceMode, user?.preferredWorkspaceMode],
  );

  useEffect(() => {
    if (!user?.userId || user.preferredWorkspaceMode || !legacyWorkspaceMode) {
      return;
    }

    workspaceModeStorage.writeLegacyMode(legacyWorkspaceMode, user.userId);
    void updateProfile({ preferredWorkspaceMode: legacyWorkspaceMode }).then((profile) => {
      if (profile?.preferredWorkspaceMode === legacyWorkspaceMode) {
        workspaceModeStorage.clearLegacyMode();
      }
    });
  }, [legacyWorkspaceMode, updateProfile, user?.preferredWorkspaceMode, user?.userId]);

  const setMode = async (nextMode: RoleMode) => {
    if (!user?.userId) {
      return;
    }
    workspaceModeStorage.writeLegacyMode(nextMode, user.userId);
    const profile = await updateProfile({ preferredWorkspaceMode: nextMode });
    if (profile?.preferredWorkspaceMode === nextMode) {
      workspaceModeStorage.clearLegacyMode();
    }
  };

  return {
    mode,
    hasGmCampaign,
    setMode,
  };
};
