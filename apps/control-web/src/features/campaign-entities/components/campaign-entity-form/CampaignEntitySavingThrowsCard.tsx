import {
  ENTITY_ABILITIES,
  getCampaignEntityAbilityModifier,
  withSignedBonus,
  type AbilityName,
  type CampaignEntityPayload,
} from "../../../../entities/campaign-entity";
import { fieldClass, rowDisplayClass } from "./constants";
import type { NewSaveKey, Translate } from "./types";

type Props = {
  form: CampaignEntityPayload;
  availableSaveAbilities: typeof ENTITY_ABILITIES;
  selectedSavingThrows: typeof ENTITY_ABILITIES;
  selectedNewSaveKey: NewSaveKey;
  setNewSaveKey: (value: NewSaveKey) => void;
  addSavingThrow: () => void;
  setSaveBonus: (key: AbilityName, value: string) => void;
  removeSavingThrow: (key: AbilityName) => void;
  t: Translate;
};

export const CampaignEntitySavingThrowsCard = ({
  form,
  availableSaveAbilities,
  selectedSavingThrows,
  selectedNewSaveKey,
  setNewSaveKey,
  addSavingThrow,
  setSaveBonus,
  removeSavingThrow,
  t,
}: Props) => (
  <div className="rounded-3xl border border-white/8 bg-white/3 p-4">
    <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
      {t("entity.form.specialSavingThrows")}
    </p>
    <p className="mt-1 text-xs text-slate-500">
      {t("entity.form.specialSavingThrowsDescription")}
    </p>

    <div className="mt-4">
      {availableSaveAbilities.length > 0 ? (
        <div className="grid gap-2 sm:grid-cols-[minmax(0,240px)_auto] sm:items-center">
          <select
            value={selectedNewSaveKey}
            onChange={(event) => setNewSaveKey(event.target.value as NewSaveKey)}
            className={`${fieldClass} min-w-0`}
          >
            {availableSaveAbilities.map((ability) => (
              <option key={ability.key} value={ability.key}>
                {ability.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={addSavingThrow}
            className="rounded-full border border-white/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-200 transition hover:border-white/20 hover:bg-white/5 sm:justify-self-start"
          >
            {t("entity.form.addSavingThrow")}
          </button>
        </div>
      ) : (
        <p className="text-xs text-slate-500">{t("entity.form.noSavingThrowsLeft")}</p>
      )}
    </div>

    {selectedSavingThrows.length === 0 ? (
      <p className="mt-4 text-sm text-slate-500">{t("entity.form.noSavingThrows")}</p>
    ) : (
      <div className="mt-4 space-y-3">
        {selectedSavingThrows.map((ability) => (
          <div key={ability.key} className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_160px_auto]">
            <div className={rowDisplayClass}>
              <div className="font-medium text-slate-100">{ability.label}</div>
              <div className="mt-1 text-xs text-slate-500">
                {t("entity.form.baseLabel")}{" "}
                {withSignedBonus(getCampaignEntityAbilityModifier(form.abilities[ability.key]))}
              </div>
            </div>
            <input
              type="number"
              value={form.savingThrows[ability.key] ?? ""}
              onChange={(event) => setSaveBonus(ability.key, event.target.value)}
              placeholder={`${ability.short} ${t("entity.form.bonusPlaceholder")}`}
              className={fieldClass}
            />
            <button
              type="button"
              onClick={() => removeSavingThrow(ability.key)}
              className="rounded-full border border-red-500/30 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-red-300 transition hover:bg-red-500/10"
            >
              {t("entity.form.removeOptional")}
            </button>
          </div>
        ))}
      </div>
    )}
  </div>
);
