import { getRace, getRaceConfigFields } from "../data/races";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { RequiredField } from "../utils/creationValidation";
import { ABILITIES, SKILL_LABELS, SKILL_NAMES } from "../constants";
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
  const configFields = getRaceConfigFields(sheet.race);
  if (!race || configFields.length === 0) return null;

  const hasError = missingRequiredFields.includes("raceConfig");

  return (
    <div className={`mt-4 rounded-[24px] border bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ${hasError ? "border-red-500/40" : "border-white/8"}`}>
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
                    const disabled = readOnly || (!checked && selected.size >= field.count);
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
            </div>
          );
        })}
      </div>
    </div>
  );
};
