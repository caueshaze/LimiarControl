import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { RequiredField } from "../utils/creationValidation";
import { getClassCreationConfig } from "../data/classCreation";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  sheet: CharacterSheet;
  pickClassToolProficiency: SheetActions["pickClassToolProficiency"];
  missingRequiredFields?: RequiredField[];
};

export const ClassToolProficiencyPicker = ({
  sheet,
  pickClassToolProficiency,
  missingRequiredFields = [],
}: Props) => {
  const { t } = useLocale();
  const config = getClassCreationConfig(sheet.class)?.toolProficiencyChoices;
  if (!config) return null;

  const chosen = new Set(sheet.classToolProficiencyChoices);
  const slotsUsed = sheet.classToolProficiencyChoices.length;
  const remaining = config.count - slotsUsed;
  const hasError = missingRequiredFields.includes("classToolProficiencies");

  return (
    <div
      className={`mt-5 rounded-[24px] border bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ${
        hasError ? "border-red-500/40" : "border-white/8"
      }`}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          {t("sheet.toolPicker.title")}
        </span>
        <span
          className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${
            remaining > 0
              ? "bg-amber-500/10 text-amber-300"
              : "bg-emerald-500/10 text-emerald-300"
          }`}
        >
          {t("sheet.toolPicker.chosen")
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
              onClick={() => pickClassToolProficiency(tool)}
              disabled={!canPick && !isChosen}
              className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold transition-all ${
                isChosen
                  ? "border-limiar-500/40 bg-limiar-500/15 text-limiar-200"
                  : canPick
                    ? "border-white/8 bg-white/[0.02] text-slate-300 hover:border-slate-400/40 hover:text-slate-100"
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
          {remaining > 1
            ? t("sheet.toolPicker.chooseMorePlural").replace("{n}", String(remaining))
            : t("sheet.toolPicker.chooseMore").replace("{n}", String(remaining))}
        </p>
      )}
    </div>
  );
};
