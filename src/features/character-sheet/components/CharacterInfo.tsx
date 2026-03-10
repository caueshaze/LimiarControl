import type { CharacterSheet, CharacterSheetMode } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { input, fieldLabel, chk } from "./styles";
import { ALIGNMENTS } from "../data/alignments";
import { RACES, getRace } from "../data/races";
import { CLASSES, getClass } from "../data/classes";
import { BACKGROUNDS, getBackground } from "../data/backgrounds";
import { safeParseInt } from "../utils/calculations";
import { ClassSkillPicker } from "./ClassSkillPicker";
import { ClassEquipmentChoices } from "./ClassEquipmentChoices";

type Props = {
  sheet: CharacterSheet;
  mode: CharacterSheetMode;
  readOnly?: boolean;
  set: SheetActions["set"];
  selectClass: SheetActions["selectClass"];
  selectBackground: SheetActions["selectBackground"];
  selectRace: SheetActions["selectRace"];
  selectClassEquipment: SheetActions["selectClassEquipment"];
  pickClassSkill: SheetActions["pickClassSkill"];
};

export const CharacterInfo = ({
  sheet,
  mode,
  readOnly = false,
  set,
  selectClass,
  selectBackground,
  selectRace,
  selectClassEquipment,
  pickClassSkill,
}: Props) => {
  const isCreation = mode === "creation";
  const raceData = getRace(sheet.race);
  const classData = getClass(sheet.class);
  const backgroundData = getBackground(sheet.background);

  return (
    <Section title="Basic Information" color="bg-limiar-500">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
        <div className="xl:col-span-5">
          <label className={fieldLabel}>Character Name</label>
          <input type="text" value={sheet.name} disabled={readOnly} onChange={(e) => set("name", e.target.value)} className={input} />
        </div>

        <div className="xl:col-span-3">
          <label className={fieldLabel}>Class</label>
          <select value={sheet.class} disabled={readOnly} onChange={(e) => selectClass(e.target.value)} className={input}>
            <option value="">Select class</option>
            {CLASSES.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
          </select>
        </div>

        <div className="xl:col-span-4">
          <label className={fieldLabel}>Race</label>
          <select value={sheet.race} disabled={readOnly} onChange={(e) => selectRace(e.target.value)} className={input}>
            <option value="">Select race</option>
            {RACES.map((r) => <option key={r.name} value={r.name}>{r.name}</option>)}
          </select>
        </div>

        <div className="xl:col-span-4">
          <label className={fieldLabel}>Background</label>
          <select value={sheet.background} disabled={readOnly} onChange={(e) => selectBackground(e.target.value)} className={input}>
            <option value="">Select background</option>
            {BACKGROUNDS.map((b) => <option key={b.name} value={b.name}>{b.name}</option>)}
          </select>
        </div>

        <div className="xl:col-span-3">
          <label className={fieldLabel}>Alignment</label>
          <select value={sheet.alignment} disabled={readOnly} onChange={(e) => set("alignment", e.target.value)} className={input}>
            <option value="">Select alignment</option>
            {ALIGNMENTS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>

        <div className="xl:col-span-3">
          <label className={fieldLabel}>Player Name</label>
          <input type="text" value={sheet.playerName} disabled={readOnly} onChange={(e) => set("playerName", e.target.value)} className={input} />
        </div>

        <div className="xl:col-span-2">
          <label className={fieldLabel}>Level</label>
          <input
            type="number" min={1} max={20} value={sheet.level} disabled={isCreation || readOnly}
            onChange={(e) => set("level", Math.max(1, Math.min(20, safeParseInt(e.target.value, 1))))}
            className={`${input} ${isCreation || readOnly ? "opacity-70" : ""}`}
          />
        </div>

        {!isCreation && !readOnly && (
          <div className="xl:col-span-2">
            <label className={fieldLabel}>Experience Points</label>
            <input
              type="number" min={0} value={sheet.experiencePoints}
              onChange={(e) => set("experiencePoints", Math.max(0, safeParseInt(e.target.value)))}
              className={input}
            />
          </div>
        )}
      </div>

      {/* Racial bonus apply */}
      <div className="mt-5 grid gap-3 xl:grid-cols-3">
        {raceData && (
          <div className="rounded-[24px] border border-white/8 bg-slate-950/55 p-4 text-xs text-slate-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Race Preview</p>
            <p className="mt-3 text-sm font-semibold text-slate-100">{raceData.name}</p>
            <p className="mt-1 leading-6">
              <span className="text-slate-300">{raceData.size}</span>
              <span className="mx-2 text-slate-600">•</span>
              <span>Speed {raceData.speed}ft</span>
              {raceData.darkvision && (
                <>
                  <span className="mx-2 text-slate-600">•</span>
                  <span>Darkvision {raceData.darkvision}ft</span>
                </>
              )}
            </p>
            {raceData.languages.length > 0 && (
              <p className="mt-2 leading-6">Languages: {raceData.languages.join(", ")}</p>
            )}
            {Object.entries(raceData.abilityBonuses).length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(raceData.abilityBonuses).map(([k, v]) => (
                  <span key={k} className="rounded-full border border-limiar-500/20 bg-limiar-500/10 px-2.5 py-1 font-semibold text-limiar-300">
                    {k.slice(0, 3).toUpperCase()} {v! >= 0 ? `+${v}` : v}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {classData && (
          <div className="rounded-[24px] border border-white/8 bg-slate-950/55 p-4 text-xs text-slate-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Class Preview</p>
            <p className="mt-3 text-sm font-semibold text-slate-100">{classData.name}</p>
            <p className="mt-1 leading-6">Hit Die {classData.hitDice}</p>
            <p className="leading-6">Saving Throws: {classData.savingThrows.join(", ")}</p>
            <p className="leading-6">Choose {classData.skillCount} class skills</p>
            {classData.spellcastingAbility && (
              <p className="mt-2 font-semibold text-violet-300">
                Spellcasting: {classData.spellcastingAbility.toUpperCase()}
              </p>
            )}
          </div>
        )}

        {backgroundData && (
          <div className="rounded-[24px] border border-white/8 bg-slate-950/55 p-4 text-xs text-slate-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Background Preview</p>
            <p className="mt-3 text-sm font-semibold text-slate-100">{backgroundData.name}</p>
            <p className="mt-1 leading-6">Feature: {backgroundData.feature}</p>
            <p className="mt-2 leading-6">Equipment: {backgroundData.startingEquipment.join(", ")}</p>
          </div>
        )}
      </div>

      {/* Class skill selection */}
      {isCreation && <ClassSkillPicker sheet={sheet} pickClassSkill={pickClassSkill} />}
      {isCreation && (
        <ClassEquipmentChoices
          className={sheet.class}
          selections={sheet.classEquipmentSelections}
          onSelect={selectClassEquipment}
        />
      )}

      {!isCreation && !readOnly && (
        <label className="mt-4 flex items-center gap-3">
          <input type="checkbox" checked={sheet.inspiration} onChange={() => set("inspiration", !sheet.inspiration)} className={chk} />
          <span className="text-sm font-semibold text-amber-400">Inspiration</span>
        </label>
      )}
    </Section>
  );
};
