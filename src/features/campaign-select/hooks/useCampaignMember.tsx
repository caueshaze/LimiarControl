import { useCallback, useEffect, useState } from "react";
import { membersRepo } from "../../../shared/api/membersRepo";
import type { RoleMode } from "../../../shared/types/role";
import { useAuth } from "../../auth";

type CampaignMember = {
  campaignId: string;
  displayName: string;
  roleMode: RoleMode;
};

export const useCampaignMember = (campaignId: string | null | undefined) => {
  const { user } = useAuth();
  const [member, setMember] = useState<CampaignMember | null>(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!campaignId || !user) {
      setMember(null);
      setError(null);
      setLoaded(false);
      return;
    }
    setLoading(true);
    try {
      const data = await membersRepo.getMe(campaignId);
      setMember(data);
      setError(null);
      setLoaded(true);
    } catch (err: { message?: string }) {
      setMember(null);
      setError(err?.message ?? "Failed to load campaign member");
      setLoaded(true);
    } finally {
      setLoading(false);
    }
  }, [campaignId, user]);

  useEffect(() => {
    let active = true;
    if (!campaignId || !user) {
      setMember(null);
      setError(null);
      setLoaded(false);
      return;
    }
    setLoading(true);
    membersRepo
      .getMe(campaignId)
      .then((data) => {
        if (!active) return;
        setMember(data);
        setError(null);
        setLoaded(true);
      })
      .catch((err: { message?: string }) => {
        if (!active) return;
        setMember(null);
        setError(err?.message ?? "Failed to load campaign member");
        setLoaded(true);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [campaignId, user]);

  return { member, memberRole: member?.roleMode ?? null, loading, loaded, error, refresh };
};
