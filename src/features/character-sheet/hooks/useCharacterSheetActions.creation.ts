import type { CharacterSheet, SkillName } from "../model/characterSheet.types";
import type { CharacterSheetHookAction } from "./useCharacterSheet.state";
import { getClass } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { getRace } from "../data/races";
import { getClassCreationConfig } from "../data/classCreation";
import { buildCreationLoadout } from "../utils/creationEquipment";
import { toggleStartingSpell } from "../utils/creationSpells";
import { validateSheet } from "../model/characterSheet.schema";
import {
  applyRaceBonusSwap,
  buildCreationSkillProficiencies,
  deriveLanguages,
  mergeToolProficiencies,
  normalizeCreationAfterBackgroundChange,
  normalizeCreationAfterClassChange,
  normalizeCreationAfterRaceChange,
} from "./useCharacterSheet.creation";

type GuardedUpdate = (updater: (sheet: CharacterSheet) => CharacterSheet) => void;
type Update = (updater: (sheet: CharacterSheet) => CharacterSheet) => void;
type SetField = <K extends keyof CharacterSheet>(key: K, value: CharacterSheet[K]) => void;
type Dispatch = (action: CharacterSheetHookAction) => void;

type Props = {
  mode: "creation" | "play";
  campaignId: string | null;
  guardedUpdate: GuardedUpdate;
  update: Update;
  set: SetField;
  dispatch: Dispatch;
  importRef: React.RefObject<HTMLInputElement | null>;
  sheet: CharacterSheet;
};

export const createCreationSheetActions = ({
  mode,
  campaignId,
  guardedUpdate,
  update,
  set,
  dispatch,
  importRef,
  sheet,
}: Props) => {
  const selectClass = (name: string) => {
    if (mode === "creation") {
      update((current) => normalizeCreationAfterClassChange(current, name, campaignId));
      return;
    }
    const cls = getClass(name);
    if (!cls) {
      guardedUpdate((current) => ({ ...current, class: name, subclass: null }));
      return;
    }
    guardedUpdate((current) => ({ ...current, class: name, subclass: null, hitDiceType: cls.hitDice }));
  };

  const selectBackground = (name: string) => {
    if (mode === "creation") {
      update((current) => normalizeCreationAfterBackgroundChange(current, name));
      return;
    }
    const background = getBackground(name);
    if (!background) return set("background", name);
    guardedUpdate((current) => ({ ...current, background: name }));
  };

  const selectRace = (name: string) => {
    guardedUpdate((current) => {
      if (mode === "creation") return normalizeCreationAfterRaceChange(current, name, campaignId);
      const race = getRace(name);
      return {
        ...current,
        race: name,
        speed: race?.speed ?? 0,
        abilities: applyRaceBonusSwap(current.abilities, current.race, name),
      };
    });
  };

  const selectSubclass = (id: string) =>
    guardedUpdate((current) => ({ ...current, subclass: id || null }));

  const selectClassEquipment = (groupId: string, optionId: string) =>
    guardedUpdate((current) => {
      if (mode !== "creation") return current;
      const nextSelections = { ...current.classEquipmentSelections, [groupId]: optionId };
      const loadout = buildCreationLoadout(current.class, current.background, nextSelections);
      return {
        ...current,
        classEquipmentSelections: nextSelections,
        inventory: loadout.inventory,
        currency: loadout.currency,
        equippedArmor: loadout.equippedArmor,
        equippedShield: loadout.equippedShield,
      };
    });

  const pickClassSkill = (skill: SkillName) =>
    guardedUpdate((current) => {
      const cls = getClass(current.class);
      if (!cls) return current;
      if (!cls.skillChoices.includes(skill)) return current;
      const bgSkills = new Set(getBackground(current.background)?.skillProficiencies ?? []);
      if (bgSkills.has(skill)) return current;
      const isChosen = current.classSkillChoices.includes(skill);
      if (!isChosen && current.classSkillChoices.length >= cls.skillCount) return current;
      const nextChoices = isChosen
        ? current.classSkillChoices.filter((entry) => entry !== skill)
        : [...current.classSkillChoices, skill];
      if (mode === "creation") {
        const skills = buildCreationSkillProficiencies(
          current.skillProficiencies,
          current.background,
          nextChoices,
        );
        return { ...current, classSkillChoices: nextChoices, skillProficiencies: skills };
      }
      const skills = { ...current.skillProficiencies };
      if (isChosen) {
        if (skills[skill] === 1) skills[skill] = 0;
      } else if (skills[skill] === 0) {
        skills[skill] = 1;
      }
      return { ...current, classSkillChoices: nextChoices, skillProficiencies: skills };
    });

  const pickClassToolProficiency = (tool: string) =>
    guardedUpdate((current) => {
      if (mode !== "creation") return current;
      const config = getClassCreationConfig(current.class)?.toolProficiencyChoices;
      if (!config) return current;
      if (!config.options.includes(tool)) return current;
      const isChosen = current.classToolProficiencyChoices.includes(tool);
      if (!isChosen && current.classToolProficiencyChoices.length >= config.count) return current;
      const nextChoices = isChosen
        ? current.classToolProficiencyChoices.filter((entry) => entry !== tool)
        : [...current.classToolProficiencyChoices, tool];
      const bgTools = getBackground(current.background)?.toolProficiencies ?? [];
      return {
        ...current,
        classToolProficiencyChoices: nextChoices,
        toolProficiencies: mergeToolProficiencies(bgTools, nextChoices),
      };
    });

  const selectLanguageChoice = (slotIndex: number, language: string) =>
    guardedUpdate((current) => {
      if (mode !== "creation") return current;
      const nextChoices = [...current.languageChoices];
      while (nextChoices.length <= slotIndex) nextChoices.push("");
      nextChoices[slotIndex] = language;
      return {
        ...current,
        languageChoices: nextChoices,
        languages: deriveLanguages(current.race, current.background, nextChoices),
      };
    });

  const toggleCreationSpellSelection = (spellName: string) =>
    guardedUpdate((current) => {
      if (mode !== "creation" || !current.spellcasting || !getClassCreationConfig(current.class)?.startingSpells) {
        return current;
      }
      const nextSpellcasting = toggleStartingSpell(
        current.spellcasting,
        current.class,
        current.abilities,
        current.level,
        spellName,
        campaignId,
      );
      return nextSpellcasting ? { ...current, spellcasting: nextSpellcasting } : current;
    });

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(sheet, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${sheet.name || "character"}-sheet.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const result = validateSheet(JSON.parse(reader.result as string));
        if (result.ok) dispatch({ type: "import_success", sheet: result.sheet });
        else dispatch({ type: "import_fail", error: result.error });
      } catch {
        dispatch({ type: "import_fail", error: "Failed to parse JSON file." });
      }
    };
    reader.readAsText(file);
    if (importRef.current) importRef.current.value = "";
  };

  const resetSheet = () => dispatch({ type: "reset" });

  return {
    selectClass,
    selectBackground,
    selectRace,
    selectSubclass,
    selectClassEquipment,
    pickClassSkill,
    pickClassToolProficiency,
    selectLanguageChoice,
    toggleCreationSpellSelection,
    handleExport,
    handleImport,
    resetSheet,
  };
};
