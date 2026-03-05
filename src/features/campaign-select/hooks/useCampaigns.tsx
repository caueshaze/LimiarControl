import type { ReactNode } from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { CampaignSystemType } from "../../../entities/campaign";
import type { Campaign } from "../../../entities/campaign";
import { campaignsRepo } from "../../../shared/api/campaignsRepo";
import { preferencesRepo } from "../../../shared/api/preferencesRepo";
import { storageKeys } from "../../../shared/lib/storage";
import { useAuth } from "../../auth";

const isCampaign = (value: Campaign): boolean =>
  Boolean(
    value?.id &&
    value?.name &&
    value?.systemType &&
    value?.createdAt &&
    Object.values(CampaignSystemType).includes(value.systemType)
  );

type CampaignContextValue = {
  campaigns: Campaign[];
  campaignsLoading: boolean;
  campaignsError: string | null;
  selectedCampaignId: string | null;
  selectedCampaign: Campaign | null;
  refreshCampaigns: () => Promise<void>;
  upsertCampaign: (campaign: Campaign) => void;
  createCampaign: (name: string, systemType: CampaignSystemType) => Promise<{
    ok: boolean;
    campaignId?: string;
    message?: string;
  }>;
  updateCampaign: (
    campaignId: string,
    name: string,
    systemType: CampaignSystemType
  ) => Promise<{
    ok: boolean;
    campaign?: Campaign;
    message?: string;
  }>;
  selectCampaign: (campaignId: string) => void;
  setSelectedCampaignLocal: (campaignId: string | null) => void;
  clearSelectedCampaign: () => void;
};

const CampaignContext = createContext<CampaignContextValue | null>(null);

const readStoredCampaignId = () => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(storageKeys.selectedCampaignId);
};

export const CampaignProvider = ({ children }: { children: ReactNode }) => {
  const { token } = useAuth();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(false);
  const [campaignsError, setCampaignsError] = useState<string | null>(null);
  const [campaignsLoaded, setCampaignsLoaded] = useState(false);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(
    readStoredCampaignId
  );

  const fetchCampaigns = useCallback(async () => {
    setCampaignsLoading(true);
    try {
      const data = await campaignsRepo.list();
      const sanitized = Array.isArray(data) ? data.filter(isCampaign) : [];
      setCampaigns(sanitized);
      setCampaignsError(null);
    } catch (error: unknown) {
      setCampaignsError((error as { message?: string })?.message ?? "Failed to load campaigns");
    } finally {
      setCampaignsLoading(false);
      setCampaignsLoaded(true);
    }
    try {
      const prefs = await preferencesRepo.get();
      if (prefs?.selectedCampaignId) {
        setSelectedCampaignId(prefs.selectedCampaignId);
      }
    } catch (error) {
      // Avoid clearing campaigns on preferences failure.
      console.warn("Preferences fetch failed", error);
    }
  }, []);

  useEffect(() => {
    if (!token) {
      setCampaigns([]);
      setCampaignsError(null);
      setCampaignsLoaded(false);
      setSelectedCampaignId(null);
      if (typeof window !== "undefined") {
        window.sessionStorage.removeItem(storageKeys.selectedCampaignId);
      }
      return;
    }
    fetchCampaigns().catch(() => {});
  }, [fetchCampaigns, token]);

  useEffect(() => {
    if (!campaignsLoaded) {
      return;
    }
    if (!selectedCampaignId) {
      return;
    }

    const exists = campaigns.some((campaign) => campaign.id === selectedCampaignId);
    if (!exists) {
      // Only clear if campaigns loaded and non-empty (avoid clearing when list is still populating)
      if (campaigns.length > 0) {
        setSelectedCampaignId(null);
        // Do NOT call preferencesRepo here — this fires when the campaign is a player-only campaign
        // (not in /me/campaigns), which would cause an infinite PUT loop with PlayerBoardPage.
      }
    }
  }, [campaigns, campaignsLoaded, selectedCampaignId]);

  const selectedCampaign = useMemo(
    () => campaigns.find((campaign) => campaign.id === selectedCampaignId) ?? null,
    [campaigns, selectedCampaignId]
  );

  const createCampaign = useCallback(
    (name: string, systemType: CampaignSystemType) => {
      if (!name.trim()) {
        return Promise.resolve({ ok: false, message: "Invalid name" });
      }
      return campaignsRepo
        .create({ name: name.trim(), system: systemType })
        .then((campaign) => {
          setCampaigns((current) => [campaign, ...current]);
          setSelectedCampaignId(campaign.id);
          if (typeof window !== "undefined") {
            window.sessionStorage.setItem(storageKeys.selectedCampaignId, campaign.id);
          }
          preferencesRepo.update({ selectedCampaignId: campaign.id }).catch(() => {});
          return { ok: true, campaignId: campaign.id };
        })
        .catch((error: { message?: string }) => ({
          ok: false,
          message: error?.message ?? "Failed to create campaign",
        }));
    },
    []
  );

  const selectCampaign = useCallback((campaignId: string) => {
    if (!campaignId || campaignId === "undefined" || selectedCampaignId === campaignId) {
      return;
    }
    setSelectedCampaignId(campaignId);
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(storageKeys.selectedCampaignId, campaignId);
    }
    preferencesRepo.update({ selectedCampaignId: campaignId }).catch(() => { });
  }, [selectedCampaignId]);

  const updateCampaign = useCallback(
    async (campaignId: string, name: string, systemType: CampaignSystemType) => {
      if (!campaignId || !name.trim()) {
        return { ok: false, message: "Invalid payload" };
      }

      return campaignsRepo
        .update(campaignId, { name: name.trim(), system: systemType })
        .then((campaign) => {
          setCampaigns((current) =>
            current.map((entry) => (entry.id === campaign.id ? campaign : entry))
          );
          return { ok: true, campaign };
        })
        .catch((error: { message?: string }) => ({
          ok: false,
          message: error?.message ?? "Failed to update campaign",
        }));
    },
    []
  );

  const setSelectedCampaignLocal = useCallback((campaignId: string | null) => {
    setSelectedCampaignId(campaignId);
    if (typeof window !== "undefined") {
      if (campaignId) {
        window.sessionStorage.setItem(storageKeys.selectedCampaignId, campaignId);
      } else {
        window.sessionStorage.removeItem(storageKeys.selectedCampaignId);
      }
    }
  }, []);

  const clearSelectedCampaign = useCallback(() => {
    setSelectedCampaignId(null);
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(storageKeys.selectedCampaignId);
    }
    preferencesRepo.update({ selectedCampaignId: null }).catch(() => { });
  }, []);

  const refreshCampaigns = useCallback(async () => {
    await fetchCampaigns();
  }, [fetchCampaigns]);

  const upsertCampaign = useCallback((campaign: Campaign) => {
    setCampaigns((current) => {
      const existingIndex = current.findIndex((item) => item.id === campaign.id);
      if (existingIndex === -1) {
        return [campaign, ...current];
      }
      const next = [...current];
      next[existingIndex] = campaign;
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({
      campaigns,
      campaignsLoading,
      campaignsError,
      selectedCampaignId,
      selectedCampaign,
      refreshCampaigns,
      upsertCampaign,
      createCampaign,
      updateCampaign,
      selectCampaign,
      setSelectedCampaignLocal,
      clearSelectedCampaign,
    }),
    [
      campaigns,
      campaignsLoading,
      campaignsError,
      selectedCampaignId,
      selectedCampaign,
      refreshCampaigns,
      upsertCampaign,
      createCampaign,
      updateCampaign,
      selectCampaign,
      setSelectedCampaignLocal,
      clearSelectedCampaign,
    ]
  );

  return <CampaignContext.Provider value={value}>{children}</CampaignContext.Provider>;
};

export const useCampaigns = () => {
  const context = useContext(CampaignContext);
  if (!context) {
    throw new Error("useCampaigns must be used within a CampaignProvider");
  }
  return context;
};
