import type { CharacterSheet, CharacterSheetMode } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { input, fieldLabel } from "./styles";
import { safeParseInt } from "../utils/calculations";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  sheet: Pick<CharacterSheet, "maxHP" | "currentHP" | "tempHP">;
  hpPercent: number;
  hpColor: string;
  mode: CharacterSheetMode;
  readOnly?: boolean;
  setCurrentHP: SheetActions["setCurrentHP"];
  setMaxHP: SheetActions["setMaxHP"];
  adjustHP: SheetActions["adjustHP"];
  set: SheetActions["set"];
};

export const HitPoints = ({
  mode,
  sheet,
  hpPercent,
  hpColor,
  readOnly = false,
  setCurrentHP,
  setMaxHP,
  adjustHP,
  set,
}: Props) => {
  const { t } = useLocale();

  if (mode === "creation") {
    return (
      <Section title={t("sheet.hp.title")} color="bg-emerald-500">
        <div className="grid grid-cols-1 gap-3">
          <div>
            <label className={fieldLabel}>{t("sheet.hp.maxDerived")}</label>
            <input type="number" min={0} value={sheet.maxHP} disabled className={`${input} opacity-70`} />
          </div>
        </div>
      </Section>
    );
  }

  return (
    <Section title={t("sheet.hp.title")} color="bg-emerald-500">
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className={fieldLabel}>{t("sheet.hp.maxHp")}</label>
          <input
            type="number" min={0} value={sheet.maxHP}
            disabled={readOnly}
            onChange={(e) => setMaxHP(safeParseInt(e.target.value))}
            className={`${input} ${readOnly ? "opacity-70" : ""}`}
          />
        </div>
        <div>
          <label className={fieldLabel}>{t("sheet.hp.currentHp")}</label>
          <input
            type="number" min={0} max={sheet.maxHP} value={sheet.currentHP}
            disabled={readOnly}
            onChange={(e) => setCurrentHP(safeParseInt(e.target.value))}
            className={`${input} ${readOnly ? "opacity-70" : ""}`}
          />
        </div>
        <div>
          <label className={fieldLabel}>{t("sheet.hp.tempHp")}</label>
          <input
            type="number" min={0} value={sheet.tempHP}
            disabled={readOnly}
            onChange={(e) => set("tempHP", Math.max(0, safeParseInt(e.target.value)))}
            className={`${input} ${readOnly ? "opacity-70" : ""}`}
          />
        </div>
      </div>

      <div className="mt-3">
        <div className="h-3 overflow-hidden rounded-full bg-slate-800">
          <div className={`h-full rounded-full transition-all ${hpColor}`} style={{ width: `${Math.min(100, hpPercent)}%` }} />
        </div>
        <p className="mt-1 text-right text-[10px] font-semibold text-slate-500">{hpPercent}%</p>
      </div>

      {!readOnly && <div className="mt-3 flex gap-2">
        {[-5, -1, 1, 5].map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => adjustHP(d)}
            className={`flex-1 rounded-xl py-1.5 text-xs font-bold transition-colors ${
              d < 0
                ? "border border-rose-800/60 bg-rose-950/30 text-rose-300 hover:bg-rose-900/40"
                : "border border-emerald-800/60 bg-emerald-950/30 text-emerald-300 hover:bg-emerald-900/40"
            }`}
          >
            {d > 0 ? `+${d}` : d}
          </button>
        ))}
      </div>}
    </Section>
  );
};
