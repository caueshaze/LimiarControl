import { useState } from "react";
import {
  CampaignSystemType,
  campaignSystemLabels,
} from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";

type CreateCampaignFormProps = {
  onCreate: (
    name: string,
    systemType: CampaignSystemType
  ) => Promise<{ ok: boolean; message?: string }>;
};

export const CreateCampaignForm = ({ onCreate }: CreateCampaignFormProps) => {
  const { t } = useLocale();
  const [name, setName] = useState("");
  const [systemType, setSystemType] = useState<CampaignSystemType>(
    CampaignSystemType.DND5E
  );
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      return;
    }

    const result = await onCreate(name, systemType);
    if (result.ok) {
      setName("");
      setSystemType(CampaignSystemType.DND5E);
      setError(null);
    } else {
      setError(result.message ?? t("campaign.form.error"));
    }
  };

  return (
    <form
      className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-4"
      onSubmit={handleSubmit}
    >
      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {t("campaign.form.name")}
        </label>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          placeholder={t("campaign.form.namePlaceholder")}
        />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {t("campaign.form.system")}
        </label>
        <select
          value={systemType}
          onChange={(event) =>
            setSystemType(event.target.value as CampaignSystemType)
          }
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
        >
          {Object.values(CampaignSystemType).map((option) => (
            <option key={option} value={option}>
              {campaignSystemLabels[option]}
            </option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        disabled={!name.trim()}
        className="w-full rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {t("campaign.form.submit")}
      </button>
      {error && <p className="text-xs text-rose-300">{error}</p>}
    </form>
  );
};
