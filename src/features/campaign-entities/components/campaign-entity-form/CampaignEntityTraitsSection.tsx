import {
  ENTITY_ABILITIES,
  ENTITY_CONDITIONS,
  ENTITY_DAMAGE_TYPES,
  type AbilityName,
  type ConditionType,
  type DamageType,
  type CampaignEntityPayload,
} from "../../../../entities/campaign-entity";
import { fieldClass } from "./constants";
import type { SetCampaignEntityField, Translate } from "./types";

type Props = {
  form: CampaignEntityPayload;
  setSenseField: (
    key: "darkvisionMeters" | "blindsightMeters" | "tremorsenseMeters" | "truesightMeters" | "passivePerception",
    value: string,
  ) => void;
  setSpellcastingField: (key: "ability" | "saveDc" | "attackBonus", value: string) => void;
  toggleListValue: <T extends string>(
    field: "damageResistances" | "damageImmunities" | "damageVulnerabilities" | "conditionImmunities",
    value: T,
  ) => void;
  t: Translate;
};

export const CampaignEntityTraitsSection = ({
  form,
  setSenseField,
  setSpellcastingField,
  toggleListValue,
  t,
}: Props) => (
  <>
    <div className="grid gap-5 xl:grid-cols-2">
      <div className="rounded-3xl border border-white/8 bg-white/3 p-4">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {t("entity.form.senses")}
        </p>
        <div className="grid grid-cols-2 gap-3">
          <input
            type="number"
            min={0}
            value={form.senses?.darkvisionMeters ?? ""}
            onChange={(event) => setSenseField("darkvisionMeters", event.target.value)}
            placeholder={t("entity.form.darkvisionMeters")}
            className={fieldClass}
          />
          <input
            type="number"
            min={0}
            value={form.senses?.blindsightMeters ?? ""}
            onChange={(event) => setSenseField("blindsightMeters", event.target.value)}
            placeholder={t("entity.form.blindsightMeters")}
            className={fieldClass}
          />
          <input
            type="number"
            min={0}
            value={form.senses?.tremorsenseMeters ?? ""}
            onChange={(event) => setSenseField("tremorsenseMeters", event.target.value)}
            placeholder={t("entity.form.tremorsenseMeters")}
            className={fieldClass}
          />
          <input
            type="number"
            min={0}
            value={form.senses?.truesightMeters ?? ""}
            onChange={(event) => setSenseField("truesightMeters", event.target.value)}
            placeholder={t("entity.form.truesightMeters")}
            className={fieldClass}
          />
          <input
            type="number"
            min={0}
            value={form.senses?.passivePerception ?? ""}
            onChange={(event) => setSenseField("passivePerception", event.target.value)}
            placeholder={t("entity.form.passivePerception")}
            className={fieldClass}
          />
        </div>
      </div>

      <div className="rounded-3xl border border-white/8 bg-white/3 p-4">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {t("entity.form.spellcasting")}
        </p>
        <div className="grid grid-cols-1 gap-3">
          <select
            value={form.spellcasting?.ability ?? ""}
            onChange={(event) => setSpellcastingField("ability", event.target.value)}
            className={fieldClass}
          >
            <option value="">{t("entity.form.spellcastingAbility")}</option>
            {ENTITY_ABILITIES.map((ability) => (
              <option key={ability.key} value={ability.key}>
                {ability.label}
              </option>
            ))}
          </select>
          <input
            type="number"
            value={form.spellcasting?.saveDc ?? ""}
            onChange={(event) => setSpellcastingField("saveDc", event.target.value)}
            placeholder={t("entity.form.spellSaveDc")}
            className={fieldClass}
          />
          <input
            type="number"
            value={form.spellcasting?.attackBonus ?? ""}
            onChange={(event) => setSpellcastingField("attackBonus", event.target.value)}
            placeholder={t("entity.form.spellAttackBonus")}
            className={fieldClass}
          />
        </div>
      </div>
    </div>

    <div className="grid gap-5 xl:grid-cols-2">
      <div>
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {t("entity.form.damageResistances")}
        </p>
        <div className="flex flex-wrap gap-2.5">
          {ENTITY_DAMAGE_TYPES.map((type) => (
            <button
              key={`resistance-${type.key}`}
              type="button"
              onClick={() => toggleListValue("damageResistances", type.key as DamageType)}
              className={`rounded-full border px-3 py-1.5 text-[11px] ${
                form.damageResistances.includes(type.key)
                  ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-200"
                  : "border-slate-700 text-slate-300 hover:bg-slate-800"
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {t("entity.form.damageImmunities")}
        </p>
        <div className="flex flex-wrap gap-2.5">
          {ENTITY_DAMAGE_TYPES.map((type) => (
            <button
              key={`immunity-${type.key}`}
              type="button"
              onClick={() => toggleListValue("damageImmunities", type.key as DamageType)}
              className={`rounded-full border px-3 py-1.5 text-[11px] ${
                form.damageImmunities.includes(type.key)
                  ? "border-sky-500/40 bg-sky-500/15 text-sky-200"
                  : "border-slate-700 text-slate-300 hover:bg-slate-800"
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {t("entity.form.damageVulnerabilities")}
        </p>
        <div className="flex flex-wrap gap-2.5">
          {ENTITY_DAMAGE_TYPES.map((type) => (
            <button
              key={`vulnerability-${type.key}`}
              type="button"
              onClick={() => toggleListValue("damageVulnerabilities", type.key as DamageType)}
              className={`rounded-full border px-3 py-1.5 text-[11px] ${
                form.damageVulnerabilities.includes(type.key)
                  ? "border-amber-500/40 bg-amber-500/15 text-amber-200"
                  : "border-slate-700 text-slate-300 hover:bg-slate-800"
              }`}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {t("entity.form.conditionImmunities")}
        </p>
        <div className="flex flex-wrap gap-2.5">
          {ENTITY_CONDITIONS.map((condition) => (
            <button
              key={`condition-${condition.key}`}
              type="button"
              onClick={() => toggleListValue("conditionImmunities", condition.key as ConditionType)}
              className={`rounded-full border px-3 py-1.5 text-[11px] ${
                form.conditionImmunities.includes(condition.key)
                  ? "border-fuchsia-500/40 bg-fuchsia-500/15 text-fuchsia-200"
                  : "border-slate-700 text-slate-300 hover:bg-slate-800"
              }`}
            >
              {condition.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  </>
);
