import type { Campaign } from "../../entities/campaign";
import { useLocale } from "../../shared/hooks/useLocale";

type NewPartyFormProps = {
  campaigns: Campaign[];
  partyName: string;
  setPartyName: (value: string) => void;
  campaignId: string;
  setCampaignId: (value: string) => void;
  onCreate: () => void;
  saving: boolean;
  error: string | null;
};

export const NewPartyForm = ({
  campaigns,
  partyName,
  setPartyName,
  campaignId,
  setCampaignId,
  onCreate,
  saving,
  error,
}: NewPartyFormProps) => {
  const { t } = useLocale();

  return (
    <section className="relative overflow-hidden rounded-4xl border border-white/8 bg-[#070712] p-6 shadow-[0_24px_70px_rgba(0,0,0,0.28)]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(167,139,250,0.16),transparent_30%),linear-gradient(180deg,rgba(15,23,42,0.9),rgba(2,6,23,0.96))]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.18)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.18)_1px,transparent_1px)] bg-size-[42px_42px] opacity-[0.08]" />
      </div>

      <div className="relative space-y-6">
        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-limiar-100/85">
            {t("gm.home.partyFormTitle")}
          </p>
          <h2 className="text-2xl font-bold text-white">{t("gm.home.newPartyAction")}</h2>
          <p className="max-w-xl text-sm leading-7 text-slate-300">
            {t("gm.home.partyFormDescription")}
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-3xl border border-white/8 bg-white/5 p-4 backdrop-blur-xl">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("gm.home.menuCampaigns")}
            </p>
            <p className="mt-3 font-display text-3xl font-bold text-white">{campaigns.length}</p>
          </div>
          <div className="rounded-3xl border border-white/8 bg-white/5 p-4 backdrop-blur-xl sm:col-span-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("home.activeCampaign")}
            </p>
            <p className="mt-3 truncate text-sm font-semibold text-white">
              {campaigns.find((campaign) => campaign.id === campaignId)?.name ??
                t("gm.home.partyCampaignMissing")}
            </p>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(220px,0.85fr)]">
          <label className="space-y-2">
            <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("gm.home.partyFormTitle")}
            </span>
            <input
              autoFocus
              value={partyName}
              onChange={(event) => setPartyName(event.target.value)}
              placeholder={t("gm.home.partyNamePlaceholder")}
              disabled={campaigns.length === 0 || saving}
              className="w-full rounded-[20px] border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-limiar-300/40 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </label>

          <label className="space-y-2">
            <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("gm.home.menuCampaigns")}
            </span>
            <select
              value={campaignId}
              onChange={(event) => setCampaignId(event.target.value)}
              disabled={campaigns.length === 0 || saving}
              className="w-full rounded-[20px] border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-limiar-300/40 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {campaigns.length === 0 && (
                <option value="">{t("gm.home.partyCampaignMissing")}</option>
              )}
              {campaigns.map((campaign) => (
                <option key={campaign.id} value={campaign.id}>
                  {campaign.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && (
          <div className="rounded-[20px] border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onCreate}
            disabled={saving || !partyName.trim() || !campaignId}
            className="rounded-full bg-limiar-500 px-6 py-3 text-xs font-bold uppercase tracking-[0.22em] text-white transition hover:bg-limiar-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? t("gm.home.partyCreating") : t("gm.home.partyCreate")}
          </button>
        </div>
      </div>
    </section>
  );
};
