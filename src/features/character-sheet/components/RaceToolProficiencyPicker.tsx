import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { RequiredField } from "../utils/creationValidation";
import { getRace } from "../data/races";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  sheet: CharacterSheet;
  pickRaceToolProficiency: SheetActions["pickRaceToolProficiency"];
  missingRequiredFields?: RequiredField[];
};

export const RaceToolProficiencyPicker = ({
  sheet,
  pickRaceToolProficiency,
  missingRequiredFields = [],
}: Props) => {
  const { t } = useLocale();
  const race = getRace(sheet.race, sheet.raceConfig);
  const config = race?.toolProficiencyChoices;
  if (!config) return null;

  const chosen = new Set(sheet.raceToolProficiencyChoices);
  const slotsUsed = sheet.raceToolProficiencyChoices.length;
  const remaining = config.count - slotsUsed;
  const hasError = missingRequiredFields.includes("raceToolProficiency");

  return (
    <div
      className={`mt-5 rounded-[24px] border bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ${
        hasError ? "border-red-500/40" : "border-white/8"
      }`}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          {race.name} — {t("sheet.raceToolPicker.title")}
        </span>
        <span
          className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${
            remaining > 0
              ? "bg-amber-500/10 text-amber-300"
              : "bg-emerald-500/10 text-emerald-300"
          }`}
        >
          {t("sheet.raceToolPicker.chosen")
            .replace("{used}", String(slotsUsed))
            .replace("{total}", String(config.count))}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {config.options.map((tool) => {
          const isChosen = chosen.has(tool);
          const canPick = isChosen || remaining > 0;

          return (
            <button
              key={tool}
              type="button"
              onClick={() => pickRaceToolProficiency(tool)}
              disabled={!canPick && !isChosen}
              className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold transition-all ${
                isChosen
                  ? "border-teal-500/40 bg-teal-500/15 text-teal-200"
                  : canPick
                    ? "border-white/8 bg-white/2 text-slate-300 hover:border-slate-400/40 hover:text-slate-100"
                    : "cursor-not-allowed border-white/5 bg-transparent text-slate-700"
              }`}
            >
              {tool}
            </button>
          );
        })}
      </div>

      {remaining > 0 && (
        <p className={`mt-2 text-[10px] ${hasError ? "text-red-400" : "text-amber-500/80"}`}>
          {t("sheet.raceToolPicker.chooseMore").replace("{n}", String(remaining))}
        </p>
      )}
    </div>
  );
};
