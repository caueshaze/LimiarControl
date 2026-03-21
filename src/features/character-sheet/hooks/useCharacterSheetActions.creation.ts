import type { CharacterSheet, SkillName } from "../model/characterSheet.types";
import type { CharacterSheetHookAction } from "./useCharacterSheet.state";
import { getClass, getSubclassLanguageGrants, hasExpertiseAtCreation } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { getRace, normalizeRaceState } from "../data/races";
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
  normalizeCreationAfterRaceConfigChange,
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
  const normalizeRaceConfigForRace = (
    raceName: string,
    raceConfig: CharacterSheet["raceConfig"],
  ): CharacterSheet["raceConfig"] => normalizeRaceState(raceName, raceConfig).raceConfig;

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
    guardedUpdate((current) => ({ ...current, background: background.id }));
  };

  const selectRace = (name: string) => {
    guardedUpdate((current) => {
      if (mode === "creation") return normalizeCreationAfterRaceChange(current, name, campaignId);
      const normalizedRace = normalizeRaceState(name, current.raceConfig);
      const race = getRace(normalizedRace.raceId, normalizedRace.raceConfig);
      return {
        ...current,
        race: normalizedRace.raceId,
        speed: race?.speed ?? 0,
        raceConfig: normalizeRaceConfigForRace(normalizedRace.raceId, normalizedRace.raceConfig),
        abilities: applyRaceBonusSwap(
          current.abilities,
          current.race,
          normalizedRace.raceId,
          current.raceConfig,
          normalizeRaceConfigForRace(normalizedRace.raceId, normalizedRace.raceConfig),
        ),
      };
    });
  };

  const selectSubclass = (id: string) =>
    guardedUpdate((current) => {
      const prevGrants = getSubclassLanguageGrants(current.class, current.subclass);
      const nextGrants = getSubclassLanguageGrants(current.class, id || null);
      // Base languages = what race + background + choices grant (no subclass influence)
      const baseLanguages = deriveLanguages(current.race, current.background, current.languageChoices);
      // Remove old subclass grants that aren't also from race/background
      const withoutOld = current.languages.filter(
        (lang) => !prevGrants.includes(lang) || baseLanguages.includes(lang),
      );
      // Add new subclass language grants (deduplicated)
      const languages = [...new Set([...withoutOld, ...nextGrants])];
      return { ...current, subclass: id || null, subclassConfig: null, languages };
    });

  const selectSubclassConfig = (key: string, value: string) =>
    guardedUpdate((current) => ({
      ...current,
      subclassConfig: { ...(current.subclassConfig ?? {}), [key]: value },
    }));

  const selectRaceConfig = (key: string, value: string | string[]) =>
    guardedUpdate((current) => {
      const nextRaceConfig = { ...(current.raceConfig ?? {}), [key]: value || null };
      if (mode === "creation") {
        return normalizeCreationAfterRaceConfigChange(current, nextRaceConfig, campaignId);
      }
      const normalizedRaceConfig = normalizeRaceConfigForRace(current.race, nextRaceConfig);
      return {
        ...current,
        raceConfig: normalizedRaceConfig,
        abilities: applyRaceBonusSwap(
          current.abilities,
          current.race,
          current.race,
          current.raceConfig,
          normalizedRaceConfig,
        ),
      };
    });

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
        // If a skill was de-selected it can no longer have expertise — re-filter
        const nextExpertise = current.expertiseChoices.filter((e) => nextChoices.includes(e));
        const raceFixedSkills = getRace(current.race, current.raceConfig)?.skillProficiencies ?? [];
        const skills = buildCreationSkillProficiencies(
          current.skillProficiencies,
          current.background,
          nextChoices,
          nextExpertise,
          raceFixedSkills,
        );
        return { ...current, classSkillChoices: nextChoices, expertiseChoices: nextExpertise, skillProficiencies: skills };
      }
      const skills = { ...current.skillProficiencies };
      if (isChosen) {
        if (skills[skill] === 1) skills[skill] = 0;
      } else if (skills[skill] === 0) {
        skills[skill] = 1;
      }
      return { ...current, classSkillChoices: nextChoices, skillProficiencies: skills };
    });

  const pickExpertise = (skill: SkillName) =>
    guardedUpdate((current) => {
      if (mode !== "creation") return current;
      const cls = getClass(current.class);
      if (!cls || !hasExpertiseAtCreation(cls, current.level)) return current;
      // Only proficient skills (class or background) can receive expertise
      const proficientSkills = new Set<SkillName>([
        ...(getBackground(current.background)?.skillProficiencies ?? []),
        ...current.classSkillChoices,
      ]);
      if (!proficientSkills.has(skill)) return current;
      const isChosen = current.expertiseChoices.includes(skill);
      if (!isChosen && current.expertiseChoices.length >= cls.expertiseCount) return current;
      const nextExpertise = isChosen
        ? current.expertiseChoices.filter((e) => e !== skill)
        : [...current.expertiseChoices, skill];
      const raceFixedSkillsExp = getRace(current.race, current.raceConfig)?.skillProficiencies ?? [];
      const skills = buildCreationSkillProficiencies(
        current.skillProficiencies,
        current.background,
        current.classSkillChoices,
        nextExpertise,
        raceFixedSkillsExp,
      );
      return { ...current, expertiseChoices: nextExpertise, skillProficiencies: skills };
    });

  const pickRaceToolProficiency = (tool: string) =>
    guardedUpdate((current) => {
      if (mode !== "creation") return current;
      const race = getRace(current.race, current.raceConfig);
      const config = race?.toolProficiencyChoices;
      if (!config) return current;
      if (!config.options.includes(tool)) return current;
      const isChosen = current.raceToolProficiencyChoices.includes(tool);
      if (!isChosen && current.raceToolProficiencyChoices.length >= config.count) return current;
      const nextChoices = isChosen
        ? current.raceToolProficiencyChoices.filter((entry) => entry !== tool)
        : [...current.raceToolProficiencyChoices, tool];
      const bgTools = getBackground(current.background)?.toolProficiencies ?? [];
      return {
        ...current,
        raceToolProficiencyChoices: nextChoices,
        toolProficiencies: mergeToolProficiencies(bgTools, current.classToolProficiencyChoices, nextChoices),
      };
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
        languages: deriveLanguages(current.race, current.background, nextChoices, current.raceConfig),
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
    selectSubclassConfig,
    selectRaceConfig,
    selectClassEquipment,
    pickClassSkill,
    pickExpertise,
    pickRaceToolProficiency,
    pickClassToolProficiency,
    selectLanguageChoice,
    toggleCreationSpellSelection,
    handleExport,
    handleImport,
    resetSheet,
  };
};
