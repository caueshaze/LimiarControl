import { DRAGONBORN_ANCESTRIES, getDragonbornAncestry } from "../data/dragonbornAncestries";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { RequiredField } from "../utils/creationValidation";
import { useLocale } from "../../../shared/hooks/useLocale";
import { fieldLabel, input } from "./styles";

type Props = {
  sheet: CharacterSheet;
  selectRaceConfig: SheetActions["selectRaceConfig"];
  missingRequiredFields?: RequiredField[];
  readOnly?: boolean;
};

export const DragonbornAncestryPicker = ({
  sheet,
  selectRaceConfig,
  missingRequiredFields = [],
  readOnly = false,
}: Props) => {
  const { t } = useLocale();
  if (sheet.race !== "dragonborn") return null;

  const missing = missingRequiredFields.includes("raceConfig");
  const ancestry = getDragonbornAncestry(sheet.raceConfig?.dragonbornAncestry);

  return (
    <div className="mt-4 rounded-[24px] border border-white/8 bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <label className={fieldLabel}>
        {t("sheet.dragonborn.ancestry")}
        <span className={`ml-0.5 ${missing ? "text-red-400" : "text-slate-500"}`}>*</span>
      </label>
      <select
        value={sheet.raceConfig?.dragonbornAncestry ?? ""}
        disabled={readOnly}
        onChange={(e) => selectRaceConfig("dragonbornAncestry", e.target.value)}
        className={`${input} ${missing ? "ring-1 ring-red-500/60 border-red-500/40" : ""}`}
      >
        <option value="">{t("sheet.dragonborn.selectAncestry")}</option>
        {DRAGONBORN_ANCESTRIES.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
      {missing ? (
        <p className="mt-0.5 text-[10px] text-red-400">{t("sheet.validation.required")}</p>
      ) : null}
      <p className="mt-2 text-xs leading-6 text-slate-400">
        {ancestry
          ? `${t("sheet.dragonborn.resistance")}: ${ancestry.resistanceType} • ${t("sheet.dragonborn.breathWeapon")}: ${ancestry.damageType}, ${ancestry.area.shape} ${ancestry.area.size}, ${t("sheet.dragonborn.save")} ${ancestry.saveAbility}`
          : t("sheet.dragonborn.pending")}
      </p>
    </div>
  );
};
