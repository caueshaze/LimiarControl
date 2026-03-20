import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { input, fieldLabel, chk, statBox } from "./styles";
import { ARMOR_PRESETS } from "../constants";
import { formatMod, safeParseInt } from "../utils/calculations";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  sheet: CharacterSheet;
  ac: number;
  initiative: number;
  acBreakdown: { label: string; value: number }[];
  set: SheetActions["set"];
  selectArmor: SheetActions["selectArmor"];
  toggleShield: SheetActions["toggleShield"];
  readOnly?: boolean;
};

export const CombatStats = ({ sheet, ac, initiative, acBreakdown, set, selectArmor, toggleShield, readOnly = false }: Props) => {
  const { t } = useLocale();

  return (
    <Section title={t("sheet.combat.title")} color="bg-rose-500">
      <div className={readOnly ? "space-y-3" : "grid gap-4 lg:grid-cols-2"}>
        <div className={readOnly ? "mx-auto w-full max-w-[27rem]" : ""}>
          <div className={`gap-3 ${readOnly ? "flex flex-wrap justify-center" : "grid [grid-template-columns:repeat(auto-fit,minmax(112px,1fr))]"}`}>
            <CombatPreviewCard label="AC" value={`${ac}`} />
            <CombatPreviewCard
              label="Initiative"
              value={formatMod(initiative)}
              valueClassName="text-limiar-400"
              note={t("sheet.combat.fromDex")}
            />
            <CombatPreviewCard
              label="Speed"
              value={sheet.speed > 0 ? `${sheet.speed}` : "-"}
              note={sheet.speed > 0 ? t("sheet.combat.baseSpeed") : t("sheet.combat.selectRace")}
            />
          </div>

          <div className={`mt-3 rounded-xl border border-slate-800/60 bg-void-950/40 p-3 ${readOnly ? "mx-auto max-w-[19rem]" : ""}`}>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-600">{t("sheet.combat.acBreakdown")}</p>
            <div className="space-y-1">
              {acBreakdown.map((part, i) => (
                <div key={i} className="flex justify-between text-xs">
                  <span className="text-slate-400">{part.label}</span>
                  <span className="font-bold text-slate-300">{formatMod(part.value)}</span>
                </div>
              ))}
              <div className="flex justify-between border-t border-slate-800 pt-1 text-xs">
                <span className="font-bold text-slate-300">{t("sheet.combat.total")}</span>
                <span className="font-bold text-slate-100">{ac}</span>
              </div>
            </div>
          </div>
        </div>

        {!readOnly && (
          <div className="space-y-3">
            <div>
              <label className={fieldLabel}>{t("sheet.combat.armor")}</label>
              <select value={sheet.equippedArmor.name} onChange={(e) => selectArmor(e.target.value)} className={input}>
                {ARMOR_PRESETS.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.name}{a.armorType !== "none" ? ` (${a.armorType}, AC ${a.baseAC})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-3">
              <input type="checkbox" checked={!!sheet.equippedShield} onChange={toggleShield} className={chk} />
              <span className="text-sm text-slate-300">
                {t("sheet.combat.shield")}{sheet.equippedShield ? ` (+${sheet.equippedShield.bonus})` : ""}
              </span>
            </label>
            <div>
              <label className={fieldLabel}>{t("sheet.combat.miscBonus")}</label>
              <input
                type="number" value={sheet.miscACBonus}
                onChange={(e) => set("miscACBonus", safeParseInt(e.target.value))}
                className={`w-20 ${input}`}
              />
            </div>
          </div>
        )}
      </div>
    </Section>
  );
};

type CombatPreviewCardProps = {
  label: string;
  value: string;
  note?: string;
  valueClassName?: string;
};

const CombatPreviewCard = ({ label, value, note, valueClassName = "text-slate-100" }: CombatPreviewCardProps) => (
  <div className={`${statBox} min-h-[96px] w-[104px] items-center justify-center px-2.5 py-2.5 text-center`}>
    <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">{label}</span>
    <span className={`mt-2 text-2xl font-bold ${valueClassName}`}>{value}</span>
    {note && <span className="mt-1 text-[10px] leading-tight text-slate-500">{note}</span>}
  </div>
);
