import type { CharacterSheet, CharacterSheetMode } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { input, fieldLabel, btnOutline } from "./styles";
import { safeParseInt } from "../utils/calculations";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  sheet: Pick<CharacterSheet, "hitDiceType" | "hitDiceTotal" | "hitDiceRemaining" | "deathSaves">;
  mode: CharacterSheetMode;
  readOnly?: boolean;
  showRestActions?: boolean;
  set: SheetActions["set"];
  useHitDie: SheetActions["useHitDie"];
  longRest: SheetActions["longRest"];
  setDeathSave: SheetActions["setDeathSave"];
};

export const HitDiceSection = ({
  mode,
  sheet,
  readOnly = false,
  showRestActions = true,
  set,
  useHitDie,
  longRest,
  setDeathSave,
}: Props) => {
  const { t } = useLocale();

  if (mode === "creation") {
    return (
      <Section title={t("sheet.hitDice.title")} color="bg-indigo-500">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={fieldLabel}>{t("sheet.hitDice.dieDerived")}</label>
            <input type="text" value={sheet.hitDiceType || "-"} disabled className={`${input} opacity-70`} />
          </div>
          <div>
            <label className={fieldLabel}>{t("sheet.hitDice.total")}</label>
            <input type="text" value={String(sheet.hitDiceTotal)} disabled className={`${input} opacity-70`} />
          </div>
        </div>
      </Section>
    );
  }

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Section title={t("sheet.hitDice.title")} color="bg-indigo-500">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={fieldLabel}>{t("sheet.hitDice.dieType")}</label>
            {readOnly ? (
              <input type="text" value={sheet.hitDiceType || "-"} disabled className={`${input} opacity-70`} />
            ) : (
              <select value={sheet.hitDiceType} disabled={readOnly} onChange={(e) => set("hitDiceType", e.target.value)} className={input}>
                {["d6", "d8", "d10", "d12"].map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            )}
          </div>
          <div>
            <label className={fieldLabel}>{t("sheet.hitDice.totalLabel")}</label>
            {readOnly ? (
              <input type="text" value={String(sheet.hitDiceTotal)} disabled className={`${input} opacity-70`} />
            ) : (
              <input
                type="number" min={0} value={sheet.hitDiceTotal}
                disabled={readOnly}
                onChange={(e) => set("hitDiceTotal", Math.max(0, safeParseInt(e.target.value)))}
                className={input}
              />
            )}
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between">
          <span className="text-sm text-slate-400">
            {t("sheet.hitDice.remaining")
              .replace("{used}", String(sheet.hitDiceRemaining))
              .replace("{total}", String(sheet.hitDiceTotal))}
          </span>
          {!readOnly && showRestActions && (
            <button
              type="button" onClick={useHitDie}
              disabled={sheet.hitDiceRemaining <= 0}
              className={`${btnOutline} ${sheet.hitDiceRemaining <= 0 ? "opacity-40" : ""}`}
            >
              {t("sheet.hitDice.use")}
            </button>
          )}
        </div>
        {!readOnly && showRestActions && (
          <button type="button" onClick={longRest} className={`mt-2 w-full ${btnOutline}`}>
            {t("sheet.hitDice.longRest")}
          </button>
        )}
      </Section>

      <Section title={t("sheet.hitDice.deathSaves")} color="bg-slate-500">
        <div className="space-y-3">
          <SaveDots label={t("sheet.hitDice.successes")} color="emerald" count={sheet.deathSaves.successes} readOnly={readOnly} onChange={(v) => setDeathSave("successes", v)} />
          <SaveDots label={t("sheet.hitDice.failures")} color="rose" count={sheet.deathSaves.failures} readOnly={readOnly} onChange={(v) => setDeathSave("failures", v)} />
          {!readOnly && (
            <button
              type="button"
              onClick={() => { setDeathSave("successes", 0); setDeathSave("failures", 0); }}
              className={`w-full ${btnOutline}`}
            >
              {t("sheet.hitDice.reset")}
            </button>
          )}
        </div>
      </Section>
    </div>
  );
};

const SaveDots = ({ label, color, count, readOnly, onChange }: { label: string; color: string; count: number; readOnly: boolean; onChange: (v: number) => void }) => (
  <div>
    <p className={`mb-2 text-xs font-semibold text-${color}-400`}>{label}</p>
    <div className="flex gap-3">
      {[0, 1, 2].map((i) => (
        <button
          key={i}
          type="button"
          disabled={readOnly}
          onClick={() => onChange(count === i + 1 ? i : i + 1)}
          className={`h-6 w-6 rounded-full border-2 transition-colors border-${color}-${i < count ? "500 bg-" + color + "-500" : "600 bg-transparent"} ${readOnly ? "cursor-not-allowed opacity-70" : ""}`}
        />
      ))}
    </div>
  </div>
);
