import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getCampaignSystemLabel,
  CampaignSystemType,
  campaignSystemLabels,
  type Campaign,
} from "../../../entities/campaign";
import { routes } from "../../../app/routes/routes";
import { useLocale } from "../../../shared/hooks/useLocale";
import { useCampaigns } from "../hooks/useCampaigns";

const NewCampaignForm = ({
  onCreate,
  onClose,
}: {
  onCreate: (name: string, system: CampaignSystemType) => Promise<{ ok: boolean; message?: string }>;
  onClose: () => void;
}) => {
  const { t } = useLocale();
  const [name, setName] = useState("");
  const [systemType, setSystemType] = useState<CampaignSystemType>(CampaignSystemType.DND5E);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const result = await onCreate(name.trim(), systemType);
      if (result.ok) {
        onClose();
      } else {
        setError(result.message ?? t("campaign.form.error"));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-2xl border border-limiar-500/20 bg-limiar-950/30 p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-limiar-300">
          {t("gm.home.campaignCreateTitle")}
        </p>
        <button
          type="button"
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 text-lg leading-none"
        >
          ×
        </button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("campaign.form.namePlaceholder")}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
          />
          <select
            value={systemType}
            onChange={(e) => setSystemType(e.target.value as CampaignSystemType)}
            className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
          >
            {Object.values(CampaignSystemType).map((opt) => (
              <option key={opt} value={opt}>
                {campaignSystemLabels[opt]}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="text-xs text-rose-300">{error}</p>}
        <div className="flex gap-3 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-700 px-5 py-2 text-xs font-semibold uppercase tracking-widest text-slate-300 hover:border-slate-500"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || !name.trim()}
            className="rounded-full bg-limiar-500 px-6 py-2 text-xs font-bold uppercase tracking-widest text-white hover:bg-limiar-400 disabled:opacity-50"
          >
            {saving ? "Creating..." : t("campaign.form.submit")}
          </button>
        </div>
      </form>
    </div>
  );
};

const CampaignCard = ({
  campaign,
  isSelected,
  onSelect,
  onOpen,
}: {
  campaign: Campaign;
  isSelected: boolean;
  onSelect: () => void;
  onOpen: () => void;
}) => {
  const { t } = useLocale();
  return (
    <article
      onClick={onSelect}
      className={`group cursor-pointer rounded-2xl border p-4 transition-all ${
        isSelected
          ? "border-limiar-500/40 bg-limiar-950/30"
          : "border-slate-800 bg-slate-950/60 hover:border-slate-700"
      }`}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {isSelected && (
              <span className="h-1.5 w-1.5 rounded-full bg-limiar-400 flex-shrink-0" />
            )}
            <h3 className="truncate text-base font-semibold text-white">{campaign.name}</h3>
            <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">
              {getCampaignSystemLabel(campaign.systemType)}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {new Date(campaign.createdAt).toLocaleDateString()}
          </p>
        </div>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onOpen(); }}
          className="flex-shrink-0 rounded-xl border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-slate-200 opacity-0 transition-opacity group-hover:opacity-100 hover:border-limiar-500/50 hover:text-limiar-300"
        >
          {t("gm.home.campaignOpen")} →
        </button>
      </div>
    </article>
  );
};

export const CampaignManagementPanel = () => {
  const { campaigns, selectedCampaignId, createCampaign, selectCampaign } = useCampaigns();
  const { t } = useLocale();
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);

  const handleCreate = async (name: string, systemType: CampaignSystemType) => {
    const result = await createCampaign(name, systemType);
    if (result.ok && result.campaignId) {
      selectCampaign(result.campaignId);
    }
    return result;
  };

  const handleOpen = (campaignId: string) => {
    selectCampaign(campaignId);
    navigate(routes.campaignEdit.replace(":campaignId", campaignId));
  };

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
      <header className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            {t("gm.home.campaignPanelTitle")}
          </p>
          <p className="mt-1 text-sm text-slate-300">
            {t("gm.home.campaignPanelDescription")}
          </p>
        </div>
        {!showForm && (
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="flex-shrink-0 rounded-full bg-limiar-500 px-4 py-2 text-xs font-bold uppercase tracking-widest text-white hover:bg-limiar-400 transition-colors"
          >
            + New
          </button>
        )}
      </header>

      {showForm && (
        <NewCampaignForm
          onCreate={handleCreate}
          onClose={() => setShowForm(false)}
        />
      )}

      <div className="space-y-2">
        {campaigns.length === 0 && !showForm && (
          <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/70 p-8 text-center text-sm text-slate-400">
            {t("campaign.empty")}
          </div>
        )}
        {campaigns.map((campaign) => (
          <CampaignCard
            key={campaign.id}
            campaign={campaign}
            isSelected={selectedCampaignId === campaign.id}
            onSelect={() => selectCampaign(campaign.id)}
            onOpen={() => handleOpen(campaign.id)}
          />
        ))}
      </div>
    </section>
  );
};
