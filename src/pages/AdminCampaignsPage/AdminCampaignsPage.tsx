import { useDeferredValue, useEffect, useState } from "react";
import { adminSystemRepo } from "../../shared/api/adminSystemRepo";
import type { AdminCampaign } from "../../entities/admin-system";
import type { CampaignSystemType } from "../../entities/campaign";
import { getCampaignSystemLabel } from "../../entities/campaign";
import { useLocale, useToast } from "../../shared/hooks";
import { Toast } from "../../shared/ui";

type SystemFilter = "ALL" | CampaignSystemType;

const formatDateTime = (value: string | null | undefined, locale: "pt" | "en") => {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(locale === "pt" ? "pt-BR" : "en-US");
};

export const AdminCampaignsPage = () => {
  const { t, locale } = useLocale();
  const { toast, showToast, clearToast } = useToast();
  const [campaigns, setCampaigns] = useState<AdminCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [systemFilter, setSystemFilter] = useState<SystemFilter>("ALL");
  const [deletingCampaignId, setDeletingCampaignId] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search);

  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const result = await adminSystemRepo.listCampaigns({
        search: deferredSearch.trim() || undefined,
        system: systemFilter === "ALL" ? undefined : systemFilter,
        limit: 200,
      });
      setCampaigns(result);
    } catch (error) {
      showToast({
        variant: "error",
        title: t("admin.campaigns.loadErrorTitle"),
        description:
          error instanceof Error ? error.message : t("admin.campaigns.loadErrorDescription"),
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadCampaigns();
  }, [deferredSearch, systemFilter]);

  const handleDelete = async (campaign: AdminCampaign) => {
    const confirmed = window.confirm(
      t("admin.campaigns.deleteConfirm").replace("{name}", campaign.name),
    );
    if (!confirmed) {
      return;
    }

    setDeletingCampaignId(campaign.id);
    try {
      await adminSystemRepo.deleteCampaign(campaign.id);
      setCampaigns((current) => current.filter((entry) => entry.id !== campaign.id));
      showToast({
        variant: "success",
        title: t("admin.campaigns.deleteSuccessTitle"),
        description: t("admin.campaigns.deleteSuccessDescription"),
      });
    } catch (error) {
      showToast({
        variant: "error",
        title: t("admin.campaigns.deleteErrorTitle"),
        description:
          error instanceof Error ? error.message : t("admin.campaigns.deleteErrorDescription"),
      });
    } finally {
      setDeletingCampaignId(null);
    }
  };

  return (
    <>
      <Toast toast={toast} onClose={clearToast} />
      <section className="space-y-6">
        <section className="rounded-[30px] border border-white/8 bg-white/4 p-6">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("admin.campaigns.filters.search")}
              </span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("admin.campaigns.filters.searchPlaceholder")}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white placeholder:text-slate-500"
              />
            </label>

            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("admin.campaigns.filters.system")}
              </span>
              <select
                value={systemFilter}
                onChange={(event) => setSystemFilter(event.target.value as SystemFilter)}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white"
              >
                <option value="ALL">{t("admin.campaigns.filters.allSystems")}</option>
                <option value="DND5E">D&D 5e</option>
                <option value="T20">Tormenta20</option>
                <option value="PF2E">Pathfinder 2e</option>
                <option value="COC">Call of Cthulhu</option>
                <option value="CUSTOM">Custom</option>
              </select>
            </label>
          </div>
        </section>

        {loading ? (
          <div className="rounded-[30px] border border-white/8 bg-white/4 p-6 text-sm text-slate-400">
            {t("admin.campaigns.loading")}
          </div>
        ) : campaigns.length === 0 ? (
          <div className="rounded-[30px] border border-white/8 bg-white/4 p-6 text-sm text-slate-400">
            {t("admin.campaigns.empty")}
          </div>
        ) : (
          <div className="space-y-4">
            {campaigns.map((campaign) => (
              <section
                key={campaign.id}
                className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.92))] p-6"
              >
                <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="text-2xl font-semibold text-white">{campaign.name}</h2>
                      <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-slate-400">
                        {getCampaignSystemLabel(campaign.systemType)}
                      </span>
                      <span className="rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-sky-100">
                        {campaign.roleMode}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300">
                      {t("admin.campaigns.gmLabel")}: {campaign.gmNames.join(", ") || "—"}
                    </p>
                    <div className="grid gap-3 sm:grid-cols-4">
                      <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                          {t("admin.campaigns.stats.members")}
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">{campaign.membersCount}</p>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                          {t("admin.campaigns.stats.parties")}
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">{campaign.partiesCount}</p>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                          {t("admin.campaigns.stats.sessions")}
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">{campaign.sessionsCount}</p>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-black/20 px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                          {t("admin.campaigns.stats.activeSessions")}
                        </p>
                        <p className="mt-2 text-xl font-bold text-white">
                          {campaign.activeSessionsCount}
                        </p>
                      </div>
                    </div>
                    <div className="grid gap-2 text-xs text-slate-500">
                      <p>
                        {t("admin.campaigns.createdAt")}:{" "}
                        {formatDateTime(campaign.createdAt, locale)}
                      </p>
                      <p>
                        {t("admin.campaigns.itemSnapshot")}:{" "}
                        {formatDateTime(campaign.itemCatalogSnapshotAt, locale)}
                      </p>
                      <p>
                        {t("admin.campaigns.spellSnapshot")}:{" "}
                        {formatDateTime(campaign.spellCatalogSnapshotAt, locale)}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-[28px] border border-rose-500/20 bg-rose-500/6 p-4 xl:w-[280px]">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-rose-200/80">
                      {t("admin.campaigns.dangerZone")}
                    </p>
                    <p className="mt-3 text-sm leading-6 text-slate-300">
                      {t("admin.campaigns.deleteHint")}
                    </p>
                    <button
                      type="button"
                      disabled={deletingCampaignId === campaign.id}
                      onClick={() => {
                        void handleDelete(campaign);
                      }}
                      className="mt-4 w-full rounded-full border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.22em] text-rose-200 transition hover:bg-rose-500/18 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {deletingCampaignId === campaign.id
                        ? t("admin.campaigns.deleting")
                        : t("admin.campaigns.deleteAction")}
                    </button>
                  </div>
                </div>
              </section>
            ))}
          </div>
        )}
      </section>
    </>
  );
};
