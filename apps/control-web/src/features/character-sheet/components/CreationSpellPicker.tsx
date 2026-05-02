import { useLocale } from "../../../shared/hooks/useLocale";
import { useEffect, useState } from "react";
import { loadSpellCatalog, isSpellCatalogLoaded } from "../../../entities/dnd-base";
import { getAvailableCreationSpells, getFixedCreationSpells } from "../utils/creationSpells";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";

type Props = {
  campaignId?: string | null;
  className: string;
  level: number;
  characterLevel: number;
  maxSpellLevel: number;
  availableCantrips: number;
  availableLeveled: number;
  selectedSpells: NonNullable<CharacterSheet["spellcasting"]>["spells"];
  onToggle: SheetActions["toggleCreationSpellSelection"];
};

export const CreationSpellPicker = ({
  campaignId = null,
  className,
  level,
  characterLevel,
  maxSpellLevel,
  availableCantrips,
  availableLeveled,
  selectedSpells,
  onToggle,
}: Props) => {
  const { t } = useLocale();
  const [ready, setReady] = useState(isSpellCatalogLoaded(campaignId));

  useEffect(() => {
    setReady(isSpellCatalogLoaded(campaignId));
  }, [campaignId]);

  useEffect(() => {
    if (ready) return;
    loadSpellCatalog(campaignId).then(() => setReady(true));
  }, [campaignId, ready]);

  if (!ready) {
    return (
      <div className="mt-5 flex items-center gap-2 text-xs text-slate-500">
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" strokeOpacity={0.25} />
          <path d="M12 2a10 10 0 019.5 6.5" strokeLinecap="round" />
        </svg>
        {t("sheet.spells.loading")}
      </div>
    );
  }

  const options = getAvailableCreationSpells(className, level, campaignId);
  const fixedSpellNames = new Set(
    getFixedCreationSpells(className, level, campaignId).map((spell) => spell.name.toLowerCase()),
  );
  const selectedNames = new Set(selectedSpells.map((spell) => spell.name.toLowerCase()));
  const selectedCantripCount = selectedSpells.filter((spell) => spell.level === 0).length;
  const selectedLeveledCount = selectedSpells.filter((spell) => spell.level > 0).length;

  const cantripTitle = t("sheet.spells.cantripGroup")
    .replace("{selected}", String(selectedCantripCount))
    .replace("{total}", String(availableCantrips));

  const leveledTitle = t("sheet.spells.leveledGroup")
    .replace("{selected}", String(selectedLeveledCount))
    .replace("{total}", String(availableLeveled));

  return (
    <div className="mt-5 space-y-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-slate-400">
        <span className="font-semibold text-slate-300">
          {t("sheet.spells.creationLevel").replace("{n}", String(characterLevel))}
        </span>
        <span>
          {t("sheet.spells.maxCircle").replace("{n}", String(maxSpellLevel))}
        </span>
        <span>{cantripTitle}</span>
        <span>{leveledTitle}</span>
      </div>

      <SpellChoiceGroup
        title={cantripTitle}
        limitReached={selectedCantripCount >= availableCantrips}
        selectedNames={selectedNames}
        names={options.cantrips.map((spell) => spell.name)}
        displayNames={options.cantrips.map((spell) => spell.namePt || spell.name)}
        fixedNames={fixedSpellNames}
        onToggle={onToggle}
      />

      {options.leveledGroups.map((group, index) => (
        <div key={`spell-level-${group.level}`}>
          <div className="border-t border-white/5" />
          <div className="pt-3">
            <SpellChoiceGroup
              title={t("sheet.spells.circleGroup")
                .replace("{n}", String(group.level))
                .replace("{selected}", String(selectedLeveledCount))
                .replace("{total}", String(availableLeveled))}
              limitReached={selectedLeveledCount >= availableLeveled}
              selectedNames={selectedNames}
              names={group.spells.map((spell) => spell.name)}
              displayNames={group.spells.map((spell) => spell.namePt || spell.name)}
              fixedNames={fixedSpellNames}
              onToggle={onToggle}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

type SpellChoiceGroupProps = {
  title: string;
  limitReached: boolean;
  selectedNames: Set<string>;
  fixedNames: Set<string>;
  names: string[];
  displayNames: string[];
  onToggle: SheetActions["toggleCreationSpellSelection"];
};

const SpellChoiceGroup = ({ title, limitReached, selectedNames, fixedNames, names, displayNames, onToggle }: SpellChoiceGroupProps) => {
  const { t } = useLocale();

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">{title}</p>
        {limitReached && <span className="text-[10px] font-semibold text-amber-300">{t("sheet.creation.limitReached")}</span>}
      </div>
      {names.length === 0 ? (
        <p className="text-[10px] italic text-slate-600">{t("sheet.spells.noSpellsInCircle")}</p>
      ) : (
        <div className="flex max-h-48 flex-wrap gap-2 overflow-y-auto pr-1">
          {names.map((name, index) => {
            const selected = selectedNames.has(name.toLowerCase());
            const fixed = fixedNames.has(name.toLowerCase());
            return (
              <button
                key={name}
                type="button"
                onClick={() => {
                  if (!fixed) onToggle(name);
                }}
                disabled={fixed}
                className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold transition-all ${
                  selected
                    ? "border-violet-500/40 bg-violet-500/15 text-violet-200"
                    : "border-white/8 bg-white/2 text-slate-300 hover:border-white/14 hover:text-slate-100"
                } ${fixed ? "cursor-default opacity-80" : ""}`}
              >
                {displayNames[index]}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
