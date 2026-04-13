import {
  ENTITY_CREATURE_TYPES,
  ENTITY_SIZES,
  type AbilityName,
  type CampaignEntityPayload,
  type CreatureType,
  type EntitySize,
  type SkillName,
} from "../../../../entities/campaign-entity";
import { fieldClass, isCreatureType, isEntitySize, sectionClass } from "./constants";
import { CampaignEntitySavingThrowsCard } from "./CampaignEntitySavingThrowsCard";
import { CampaignEntitySkillsCard } from "./CampaignEntitySkillsCard";
import { CampaignEntityTraitsSection } from "./CampaignEntityTraitsSection";
import type {
  NewSaveKey,
  NewSkillKey,
  SetCampaignEntityField,
  Translate,
} from "./types";

type Props = {
  form: CampaignEntityPayload;
  showAdvanced: boolean;
  setShowAdvanced: (value: boolean | ((value: boolean) => boolean)) => void;
  setField: SetCampaignEntityField;
  selectedSavingThrows: typeof import("../../../../entities/campaign-entity").ENTITY_ABILITIES;
  selectedSkills: typeof import("../../../../entities/campaign-entity").ENTITY_SKILLS;
  availableSaveAbilities: typeof import("../../../../entities/campaign-entity").ENTITY_ABILITIES;
  availableSkills: typeof import("../../../../entities/campaign-entity").ENTITY_SKILLS;
  selectedNewSaveKey: NewSaveKey;
  selectedNewSkillKey: NewSkillKey;
  setNewSaveKey: (value: NewSaveKey) => void;
  setNewSkillKey: (value: NewSkillKey) => void;
  addSavingThrow: () => void;
  addSkill: () => void;
  setSaveBonus: (key: AbilityName, value: string) => void;
  setSkillBonus: (key: SkillName, value: string) => void;
  removeSavingThrow: (key: AbilityName) => void;
  removeSkill: (key: SkillName) => void;
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

export const CampaignEntityAdvancedSection = ({
  form,
  showAdvanced,
  setShowAdvanced,
  setField,
  selectedSavingThrows,
  selectedSkills,
  availableSaveAbilities,
  availableSkills,
  selectedNewSaveKey,
  selectedNewSkillKey,
  setNewSaveKey,
  setNewSkillKey,
  addSavingThrow,
  addSkill,
  setSaveBonus,
  setSkillBonus,
  removeSavingThrow,
  removeSkill,
  setSenseField,
  setSpellcastingField,
  toggleListValue,
  t,
}: Props) => (
  <div className={sectionClass}>
    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {t("entity.form.advancedSection")}
        </p>
        <p className="mt-2 text-sm leading-7 text-slate-400">
          {t("entity.form.advancedDescription")}
        </p>
      </div>
      <button
        type="button"
        onClick={() => setShowAdvanced((value) => !value)}
        className="rounded-full border border-white/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-white/20 hover:bg-white/5"
      >
        {showAdvanced ? t("entity.form.hideAdvanced") : t("entity.form.showAdvanced")}
      </button>
    </div>

    {showAdvanced ? (
      <div className="mt-5 space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <select
            value={form.size ?? ""}
            onChange={(event) =>
              setField("size", event.target.value === "" ? null : isEntitySize(event.target.value) ? event.target.value : null)
            }
            className={fieldClass}
          >
            <option value="">{t("entity.form.size")}</option>
            {ENTITY_SIZES.map((size) => (
              <option key={size.key} value={size.key}>
                {size.label}
              </option>
            ))}
          </select>
          <select
            value={form.creatureType ?? ""}
            onChange={(event) =>
              setField(
                "creatureType",
                event.target.value === "" ? null : isCreatureType(event.target.value) ? event.target.value : null,
              )
            }
            className={fieldClass}
          >
            <option value="">{t("entity.form.creatureType")}</option>
            {ENTITY_CREATURE_TYPES.map((type) => (
              <option key={type.key} value={type.key}>
                {type.label}
              </option>
            ))}
          </select>
          <input
            value={form.creatureSubtype ?? ""}
            onChange={(event) => setField("creatureSubtype", event.target.value)}
            placeholder={t("entity.form.creatureSubtype")}
            className={fieldClass}
          />
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          <CampaignEntitySavingThrowsCard
            form={form}
            availableSaveAbilities={availableSaveAbilities}
            selectedSavingThrows={selectedSavingThrows}
            selectedNewSaveKey={selectedNewSaveKey}
            setNewSaveKey={setNewSaveKey}
            addSavingThrow={addSavingThrow}
            setSaveBonus={setSaveBonus}
            removeSavingThrow={removeSavingThrow}
            t={t}
          />
          <CampaignEntitySkillsCard
            form={form}
            availableSkills={availableSkills}
            selectedSkills={selectedSkills}
            selectedNewSkillKey={selectedNewSkillKey}
            setNewSkillKey={setNewSkillKey}
            addSkill={addSkill}
            setSkillBonus={setSkillBonus}
            removeSkill={removeSkill}
            t={t}
          />
        </div>

        <CampaignEntityTraitsSection
          form={form}
          setSenseField={setSenseField}
          setSpellcastingField={setSpellcastingField}
          toggleListValue={toggleListValue}
          t={t}
        />
      </div>
    ) : (
      <p className="mt-4 text-sm text-slate-500">{t("entity.form.advancedCollapsedHint")}</p>
    )}
  </div>
);
