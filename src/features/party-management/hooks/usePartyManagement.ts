import { useCallback, useEffect, useState } from "react";
import type { Campaign } from "../../../entities/campaign";
import { useAuth } from "../../auth";
import { partiesRepo, type PartySummary } from "../../../shared/api/partiesRepo";

type CreatePartyResult = {
  ok: boolean;
  party?: PartySummary;
  message?: string;
};

export const usePartyManagement = (campaigns: Campaign[]) => {
  const { user } = useAuth();
  const [parties, setParties] = useState<PartySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [partyName, setPartyName] = useState("");
  const [campaignId, setCampaignId] = useState(campaigns[0]?.id ?? "");

  useEffect(() => {
    if (!campaigns.some((campaign) => campaign.id === campaignId)) {
      setCampaignId(campaigns[0]?.id ?? "");
    }
  }, [campaignId, campaigns]);

  const refreshParties = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await partiesRepo.listMine();
      const myParties = Array.isArray(data)
        ? data
            .filter((entry) => !user?.userId || entry.gmUserId === user.userId)
            .sort((left, right) => right.createdAt.localeCompare(left.createdAt))
        : [];
      setParties(myParties);
    } catch (fetchError: any) {
      setError(fetchError?.message ?? "Failed to load parties");
      setParties([]);
    } finally {
      setLoading(false);
    }
  }, [user?.userId]);

  useEffect(() => {
    refreshParties().catch(() => {});
  }, [refreshParties]);

  const createParty = useCallback(async (): Promise<CreatePartyResult> => {
    if (!campaignId || !partyName.trim()) {
      return { ok: false, message: "Invalid payload" };
    }

    setSaving(true);
    setError(null);

    try {
      const party = await partiesRepo.create({
        campaignId,
        name: partyName.trim(),
      });
      setPartyName("");
      await refreshParties();
      return { ok: true, party };
    } catch (saveError: any) {
      const message = saveError?.message ?? "Failed to create party";
      setError(message);
      return { ok: false, message };
    } finally {
      setSaving(false);
    }
  }, [campaignId, partyName, refreshParties]);

  return {
    parties,
    loading,
    error,
    saving,
    partyName,
    setPartyName,
    campaignId,
    setCampaignId,
    createParty,
    refreshParties,
  };
};
