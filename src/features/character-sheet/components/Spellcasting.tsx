import type { AbilityName, CharacterSheet, Spell } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { RequiredField } from "../utils/creationValidation";
import { Section, RemoveBtn } from "./Section";
import { input, fieldLabel, btnPrimary, btnDanger, chk } from "./styles";
import { ABILITIES, SPELL_SCHOOLS } from "../constants";
import { computeSpellAttack, computeSpellSaveDC, formatMod, safeParseInt } from "../utils/calculations";
import { getClassCreationConfig } from "../data/classCreation";
import { getStartingSpellLimits } from "../utils/creationSpells";
import { CreationSpellPicker } from "./CreationSpellPicker";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";

type Props = {
  campaignId?: string | null;
  className?: string;
  spellcasting: CharacterSheet["spellcasting"];
  abilities: CharacterSheet["abilities"];
  level: number;
  readOnly?: boolean;
  missingRequiredFields?: RequiredField[];
  onEnable: SheetActions["enableSpellcasting"];
  onDisable: SheetActions["disableSpellcasting"];
  onSetAbility: SheetActions["setSpellAbility"];
  onSetSlot: SheetActions["setSpellSlot"];
  onAddSpell: SheetActions["addSpell"];
  onRemoveSpell: SheetActions["removeSpell"];
  onUpdateSpell: SheetActions["updateSpell"];
  onToggleCreationSpell?: SheetActions["toggleCreationSpellSelection"];
};

export const Spellcasting = ({
  campaignId = null,
  className = "",
  spellcasting, abilities, level,
  readOnly = false,
  missingRequiredFields = [],
  onEnable, onDisable, onSetAbility,
  onSetSlot, onAddSpell, onRemoveSpell, onUpdateSpell,
  onToggleCreationSpell,
}: Props) => {
  const { t } = useLocale();
  const creationConfig = className ? getClassCreationConfig(className)?.startingSpells : null;
  const hasSpellError = missingRequiredFields.includes("cantrips") || missingRequiredFields.includes("leveledSpells");

  // In creation mode, hide the section entirely if the class has no spellcasting config.
  // The spellcasting data is auto-created by normalizeCreationAfterClassChange when the class has startingSpells.
  if (!spellcasting) {
    if (readOnly && !creationConfig) {
      // Creation mode, non-caster class — don't show anything
      return null;
    }
    if (readOnly) {
      // Creation mode, caster class but spellcasting somehow null — shouldn't happen, but show loading
      return (
        <Section title={t("sheet.spells.title")} color="bg-violet-500">
          <p className="py-4 text-xs text-slate-500">{t("sheet.spells.noSpellsCreation")}</p>
        </Section>
      );
    }
    return (
      <Section
        title={t("sheet.spells.title")}
        color="bg-violet-500"
        defaultOpen={false}
      >
        <div className="flex flex-col items-center gap-3 py-4">
          <svg className="h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
          <p className="text-xs text-slate-500">{t("sheet.spells.noSpells")}</p>
          <button type="button" onClick={onEnable} className={btnPrimary}>
            {t("sheet.spells.enable")}
          </button>
        </div>
      </Section>
    );
  }

  const abilityScore = abilities[spellcasting.ability];
  const saveDC = computeSpellSaveDC(level, abilityScore);
  const atkBonus = computeSpellAttack(level, abilityScore);
  const startingSpellLimits = className ? getStartingSpellLimits(className, abilities, level) : null;

  return (
    <Section title={t("sheet.spells.title")} color="bg-violet-500">
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className={fieldLabel}>{t("sheet.spells.ability")}</label>
          {readOnly ? (
            <input
              type="text"
              value={spellcasting.ability.toUpperCase()}
              disabled
              className={`${input} opacity-70`}
              style={{ width: "auto" }}
            />
          ) : (
            <select
              value={spellcasting.ability}
              onChange={(e) => onSetAbility(e.target.value as AbilityName)}
              className={input}
              style={{ width: "auto" }}
            >
              {ABILITIES.map((a) => (
                <option key={a.key} value={a.key}>{a.label}</option>
              ))}
            </select>
          )}
        </div>
        <div className="flex gap-4 text-sm">
          <div className="text-center">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{t("sheet.spells.saveDC")}</div>
            <div className="font-bold text-violet-300">{saveDC}</div>
          </div>
          <div className="text-center">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{t("sheet.spells.atkBonus")}</div>
            <div className="font-bold text-violet-300">{formatMod(atkBonus)}</div>
          </div>
        </div>
        {!readOnly && (
          <button type="button" onClick={onDisable} className={`ml-auto ${btnDanger}`}>
            {t("sheet.spells.remove")}
          </button>
        )}
      </div>

      {readOnly && startingSpellLimits && creationConfig && onToggleCreationSpell && (
        <>
          <div className={`mt-4 rounded-2xl border p-4 px-4 py-3 text-xs text-slate-400 ${hasSpellError ? "border-red-500/30 bg-red-950/20" : "border-white/6 bg-white/3"}`}>
            <p className="font-semibold text-slate-200">
              {t("sheet.spells.levelSlots").replace("{n}", "1")}: <span className="text-violet-300">{startingSpellLimits.levelOneSlots}</span>
            </p>
            <p className="mt-1">
              {spellcasting.mode === "spellbook"
                ? t("sheet.spells.spellbookMode")
                : spellcasting.mode === "prepared"
                  ? t("sheet.spells.prepMode")
                  : t("sheet.spells.knownMode")}
            </p>
          </div>
          <CreationSpellPicker
            campaignId={campaignId}
            className={className}
            availableCantrips={startingSpellLimits.cantrips}
            availableLeveled={startingSpellLimits.leveledSpells}
            selectedSpells={spellcasting.spells}
            onToggle={onToggleCreationSpell}
          />
        </>
      )}

      {!readOnly && <div className="mt-4">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">{t("sheet.spells.slotsTitle")}</div>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 9 }, (_, i) => i + 1).map((lvl) => {
            const slot = spellcasting.slots[lvl] ?? { max: 0, used: 0 };
            if (slot.max === 0 && slot.used === 0) return null;
            return (
              <SlotPip key={lvl} level={lvl} slot={slot} onSetSlot={onSetSlot} />
            );
          })}
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-5 md:grid-cols-9">
          {Array.from({ length: 9 }, (_, i) => i + 1).map((lvl) => {
            const slot = spellcasting.slots[lvl] ?? { max: 0, used: 0 };
            return (
              <div key={lvl} className="flex flex-col items-center gap-1">
                <span className="text-[9px] font-semibold uppercase text-slate-600">Lv{lvl}</span>
                <input
                  type="number" min={0} max={9} value={slot.max}
                  onChange={(e) => onSetSlot(lvl, "max", safeParseInt(e.target.value))}
                  className="w-full rounded-lg border border-white/10 bg-void-900/50 py-1 text-center text-xs font-bold text-slate-100 focus:border-violet-500 focus:outline-none"
                  title={`Level ${lvl} max slots`}
                />
                <input
                  type="number" min={0} max={slot.max} value={slot.used}
                  onChange={(e) => onSetSlot(lvl, "used", safeParseInt(e.target.value))}
                  className="w-full rounded-lg border border-white/10 bg-void-900/50 py-1 text-center text-xs text-slate-400 focus:border-violet-500 focus:outline-none"
                  title={`Level ${lvl} used slots`}
                />
              </div>
            );
          })}
        </div>
        <div className="mt-1 flex justify-center gap-6 text-[10px] text-slate-600">
          <span>{t("sheet.spells.slotsHint")}</span>
        </div>
      </div>}

      {!readOnly && <div className="mt-4">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">{t("sheet.spells.knownTitle")}</div>
        <div className="space-y-2">
          {spellcasting.spells.map((spell) => (
            <SpellRow key={spell.id} spell={spell} onRemove={onRemoveSpell} onUpdate={onUpdateSpell} t={t} />
          ))}
          {spellcasting.spells.length === 0 && (
            <p className="py-2 text-center text-xs text-slate-600">{t("sheet.spells.emptySpells")}</p>
          )}
        </div>
        <button type="button" onClick={onAddSpell} className={`mt-3 ${btnPrimary}`}>
          {t("sheet.spells.addSpell")}
        </button>
      </div>}
    </Section>
  );
};

type SlotPipProps = {
  level: number;
  slot: { max: number; used: number };
  onSetSlot: SheetActions["setSpellSlot"];
};

const SlotPip = ({ level, slot, onSetSlot }: SlotPipProps) => (
  <div className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-void-950/60 px-2.5 py-1">
    <span className="text-[10px] font-bold text-violet-400">L{level}</span>
    {Array.from({ length: slot.max }, (_, i) => (
      <button
        key={i}
        type="button"
        onClick={() => onSetSlot(level, "used", i < slot.used ? i : i + 1)}
        title={i < slot.used ? "Mark unused" : "Mark used"}
        className={`h-3 w-3 rounded-full border transition-colors ${
          i < slot.used
            ? "border-slate-600 bg-slate-700"
            : "border-violet-500 bg-violet-500/40"
        }`}
      />
    ))}
  </div>
);

type SpellRowProps = {
  spell: Spell;
  onRemove: SheetActions["removeSpell"];
  onUpdate: SheetActions["updateSpell"];
  t: (key: LocaleKey) => string;
};

const SpellRow = ({ spell, onRemove, onUpdate, t }: SpellRowProps) => (
  <div className="flex items-start gap-2 rounded-xl border border-slate-800/60 bg-void-950/40 p-3">
    <div className="flex-1 grid grid-cols-2 gap-2 sm:grid-cols-4">
      <div className="sm:col-span-2">
        <label className={fieldLabel}>{t("sheet.spells.spellName")}</label>
        <input
          type="text" placeholder={t("sheet.spells.namePlaceholder")} value={spell.name}
          onChange={(e) => onUpdate(spell.id, "name", e.target.value)}
          className={input}
        />
      </div>
      <div>
        <label className={fieldLabel}>{t("sheet.spells.level")}</label>
        <select value={spell.level} onChange={(e) => onUpdate(spell.id, "level", safeParseInt(e.target.value))} className={input}>
          <option value={0}>{t("sheet.spells.cantrip")}</option>
          {Array.from({ length: 9 }, (_, i) => i + 1).map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      </div>
      <div>
        <label className={fieldLabel}>{t("sheet.spells.school")}</label>
        <select value={spell.school} onChange={(e) => onUpdate(spell.id, "school", e.target.value)} className={input}>
          {SPELL_SCHOOLS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="sm:col-span-3">
        <label className={fieldLabel}>{t("sheet.equipment.notes")}</label>
        <input
          type="text" placeholder={t("sheet.spells.notesPlaceholder")} value={spell.notes}
          onChange={(e) => onUpdate(spell.id, "notes", e.target.value)}
          className={input}
        />
      </div>
      <div className="flex items-end pb-1">
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input
            type="checkbox" checked={spell.prepared}
            onChange={() => onUpdate(spell.id, "prepared", !spell.prepared)}
            className={chk}
          />
          {t("sheet.spells.prepared")}
        </label>
      </div>
    </div>
    <RemoveBtn onClick={() => onRemove(spell.id)} title="Remove spell" />
  </div>
);
