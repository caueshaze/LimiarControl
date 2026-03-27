import { LANGUAGE_CHOICE_SLOT } from "../data/languages";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { Race } from "../data/races";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  raceData: Race;
  sheet: CharacterSheet;
};

export const RacePreviewCard = ({ raceData, sheet }: Props) => {
  const { t } = useLocale();

  const fixedLanguages = raceData.languages.filter((language) => language !== LANGUAGE_CHOICE_SLOT);
  const choiceCount = raceData.languages.filter((language) => language === LANGUAGE_CHOICE_SLOT).length;
  const languageParts = [...fixedLanguages];
  if (choiceCount > 0) languageParts.push(`+${choiceCount} ${t("sheet.languages.toChoose")}`);

  return (
    <div className="rounded-[24px] border border-white/8 bg-slate-950/55 p-4 text-xs text-slate-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">{t("sheet.basicInfo.racePreview")}</p>
      <p className="mt-3 text-sm font-semibold text-slate-100">{raceData.name}</p>
      <p className="mt-1 leading-6">
        <span className="text-slate-300">{raceData.size}</span>
        <span className="mx-2 text-slate-600">•</span>
        <span>{t("sheet.basicInfo.speed")} {raceData.speedMeters}m</span>
        {raceData.darkvisionMeters ? (
          <>
            <span className="mx-2 text-slate-600">•</span>
            <span>{t("sheet.basicInfo.darkvision")} {raceData.darkvisionMeters}m</span>
          </>
        ) : null}
      </p>
      {languageParts.length > 0 ? (
        <p className="mt-2 leading-6">{t("sheet.basicInfo.languages")}: {languageParts.join(", ")}</p>
      ) : null}
      {Object.entries(raceData.abilityBonuses).length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(raceData.abilityBonuses).map(([key, value]) => (
            <span key={key} className="rounded-full border border-limiar-500/20 bg-limiar-500/10 px-2.5 py-1 font-semibold text-limiar-300">
              {key.slice(0, 3).toUpperCase()} {value! >= 0 ? `+${value}` : value}
            </span>
          ))}
        </div>
      ) : null}
      {raceData.traits.length > 0 ? (
        <div className="mt-3 space-y-1">
          {raceData.traits.map((trait) => (
            <p key={trait} className="leading-6 text-slate-300">{trait}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
};
