import { getRace, getRaceConfigFields } from "../data/races";
import {
  DRAGONBORN_DRACONIC_ANCESTRY_RACE_CONFIG_KEY,
  resolveDragonbornLineageState,
} from "../data/dragonbornAncestries";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { RequiredField } from "../utils/creationValidation";
import { ABILITIES, SKILL_LABELS, SKILL_NAMES } from "../constants";
import { getBlockedRaceConfigSkills } from "../utils/raceConfigSkills";
import { getAbilityLabel } from "../utils/abilityLabels";
import { chk, fieldLabel, input } from "./styles";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  sheet: CharacterSheet;
  selectRaceConfig: SheetActions["selectRaceConfig"];
  missingRequiredFields?: RequiredField[];
  readOnly?: boolean;
};

export const RaceConfigPicker = ({
  sheet,
  selectRaceConfig,
  missingRequiredFields = [],
  readOnly = false,
}: Props) => {
  const { t } = useLocale();
  const race = getRace(sheet.race, sheet.raceConfig);
  const dragonbornLineage = resolveDragonbornLineageState({
    raceId: sheet.race,
    raceConfig: sheet.raceConfig,
  });
  const configFields = getRaceConfigFields(sheet.race);
  if (!race || configFields.length === 0) return null;

  const hasError = missingRequiredFields.includes("raceConfig");
  const formatBreathShape = (shape: string | null) => {
    if (shape === "line") return "linha";
    if (shape === "cone") return "cone";
    return shape ?? "-";
  };

  return (
    <div className={`mt-4 rounded-3xl border bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ${hasError ? "border-red-500/40" : "border-white/8"}`}>
      <div className="mb-3">
        <span className={fieldLabel}>{t("sheet.raceConfig.title")}</span>
        {hasError ? <p className="mt-0.5 text-[10px] text-red-400">{t("sheet.validation.required")}</p> : null}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {configFields.map((field) => {
          const requiredMark = field.required ? <span className={`ml-0.5 ${hasError ? "text-red-400" : "text-slate-500"}`}>*</span> : null;

          if (field.kind === "ability_multi") {
            const selected = new Set(sheet.raceConfig?.[field.key] ?? []);
            const options = ABILITIES.filter((ability) => !field.exclude?.includes(ability.key));
            const hasFieldError = hasError && selected.size < field.count;

            return (
              <div key={field.key} className="md:col-span-2">
                <label className={fieldLabel}>
                  {field.label}
                  {requiredMark}
                </label>
                <p className="mb-3 text-xs text-slate-400">
                  Escolha {field.count} atributos distintos.
                </p>
                <div className={`grid gap-2 sm:grid-cols-2 lg:grid-cols-3 ${hasFieldError ? "rounded-2xl border border-red-500/30 p-2" : ""}`}>
                  {options.map((ability) => {
                    const checked = selected.has(ability.key);
                    const disabled = readOnly || (!checked && selected.size >= field.count);
                    return (
                      <label
                        key={ability.key}
                        className={`flex items-center gap-3 rounded-2xl border px-3 py-2 text-sm transition-colors ${checked ? "border-limiar-500/40 bg-limiar-500/10 text-limiar-100" : "border-white/8 bg-slate-950/50 text-slate-300"} ${disabled ? "opacity-60" : "cursor-pointer hover:border-limiar-500/30"}`}
                      >
                        <input
                          type="checkbox"
                          className={chk}
                          checked={checked}
                          disabled={disabled}
                          onChange={() => {
                            const next = checked
                              ? [...selected].filter((entry) => entry !== ability.key)
                              : [...selected, ability.key];
                            selectRaceConfig(field.key, next);
                          }}
                        />
                        <span>{ability.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          }

          if (field.kind === "skill_multi") {
            const selected = new Set(sheet.raceConfig?.[field.key] ?? []);
            const blockedSkills = getBlockedRaceConfigSkills(
              sheet,
              field.key as "halfElfSkillChoices",
            );
            const hasFieldError = hasError && selected.size < field.count;
            return (
              <div key={field.key} className="md:col-span-2">
                <label className={fieldLabel}>
                  {field.label}
                  {requiredMark}
                </label>
                <p className="mb-3 text-xs text-slate-400">
                  Escolha {field.count} perícias distintas.
                </p>
                <div className={`grid gap-2 sm:grid-cols-2 lg:grid-cols-3 ${hasFieldError ? "rounded-2xl border border-red-500/30 p-2" : ""}`}>
                  {SKILL_NAMES.map((skill) => {
                    const checked = selected.has(skill);
                    const disabled = readOnly || (!checked && (selected.size >= field.count || blockedSkills.has(skill)));
                    return (
                      <label
                        key={skill}
                        className={`flex items-center gap-3 rounded-2xl border px-3 py-2 text-sm transition-colors ${checked ? "border-limiar-500/40 bg-limiar-500/10 text-limiar-100" : "border-white/8 bg-slate-950/50 text-slate-300"} ${disabled ? "opacity-60" : "cursor-pointer hover:border-limiar-500/30"}`}
                      >
                        <input
                          type="checkbox"
                          className={chk}
                          checked={checked}
                          disabled={disabled}
                          onChange={() => {
                            const next = checked
                              ? [...selected].filter((entry) => entry !== skill)
                              : [...selected, skill];
                            selectRaceConfig(field.key, next);
                          }}
                        />
                        <span>{SKILL_LABELS[skill]}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          }

          return (
            <div key={field.key}>
              <label className={fieldLabel}>
                {field.label}
                {requiredMark}
              </label>
              <select
                value={sheet.raceConfig?.[field.key] ?? ""}
                disabled={readOnly}
                onChange={(event) => selectRaceConfig(field.key, event.target.value)}
                className={`${input} ${hasError && !sheet.raceConfig?.[field.key] ? "ring-1 ring-red-500/60 border-red-500/40" : ""}`}
              >
                <option value="">{t("sheet.raceConfig.select")}</option>
                {field.options.map((option) => (
                  <option key={option.id} value={option.id}>{option.name}</option>
                ))}
              </select>
              {field.key === DRAGONBORN_DRACONIC_ANCESTRY_RACE_CONFIG_KEY && (
                dragonbornLineage.ancestryLabel ? (
                  <>
                    <p className="mt-2 text-[11px] text-slate-400">
                      {t("sheet.dragonborn.ancestry")}: <span className="font-semibold text-slate-200">{dragonbornLineage.ancestryLabel}</span>
                      {dragonbornLineage.resistanceType && (
                        <>
                          {" "}· {t("sheet.dragonborn.resistance")}: <span className="font-semibold text-slate-200">{dragonbornLineage.resistanceType}</span>
                        </>
                      )}
                      {dragonbornLineage.damageType && dragonbornLineage.breathWeaponShape && dragonbornLineage.breathWeaponAreaSize && (
                        <>
                          {" "}· {t("sheet.dragonborn.breathWeapon")}: <span className="font-semibold text-slate-200">{dragonbornLineage.damageType}, {formatBreathShape(dragonbornLineage.breathWeaponShape)} {dragonbornLineage.breathWeaponAreaSize}</span>
                        </>
                      )}
                      {dragonbornLineage.breathWeaponSaveType && (
                        <>
                          {" "}· {t("sheet.dragonborn.save")}: <span className="font-semibold text-slate-200">{getAbilityLabel(dragonbornLineage.breathWeaponSaveType, t)}</span>
                        </>
                      )}
                    </p>
                    <details className="mt-2 rounded-xl border border-white/8 bg-void-900/40 px-3 py-2 text-[11px] text-slate-300">
                      <summary className="cursor-pointer font-semibold uppercase tracking-[0.18em] text-slate-400">
                        {t("sheet.dragonborn.debugTitle")}
                      </summary>
                      <div className="mt-2 grid gap-1 font-mono text-[11px] text-slate-300/90">
                        <div>{t("sheet.dragonborn.debugAncestry")}: {dragonbornLineage.ancestry ?? "-"}</div>
                        <div>{t("sheet.dragonborn.debugDamageType")}: {dragonbornLineage.damageType ?? "-"}</div>
                        <div>{t("sheet.dragonborn.debugResistanceType")}: {dragonbornLineage.resistanceType ?? "-"}</div>
                        <div>{t("sheet.dragonborn.debugBreathShape")}: {dragonbornLineage.breathWeaponShape ?? "-"}</div>
                        <div>{t("sheet.dragonborn.debugBreathSaveType")}: {dragonbornLineage.breathWeaponSaveType ?? "-"}</div>
                      </div>
                    </details>
                  </>
                ) : (
                  <p className="mt-2 text-[11px] text-amber-300/90">{t("sheet.dragonborn.pending")}</p>
                )
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
