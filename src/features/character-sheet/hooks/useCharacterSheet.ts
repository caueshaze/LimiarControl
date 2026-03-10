import { useCallback, useEffect, useReducer, useRef } from "react";
import { nanoid } from "nanoid";
import type {
  AbilityName,
  CharacterSheet,
  CharacterSheetMode,
  ConditionName,
  InventoryItem,
  ProficiencyLevel,
  SkillName,
  Spell,
  SpellcastingData,
  Weapon,
} from "../model/characterSheet.types";
import { validateSheet } from "../model/characterSheet.schema";
import { INITIAL_SHEET } from "../model/initialSheet";
import {
  ABILITY_SCORE_MAX,
  ABILITY_SCORE_MIN,
  ABILITY_SCORE_POOL,
  ARMOR_PRESETS,
  STANDARD_ARRAY,
} from "../constants";
import {
  clampHP,
  computeAbilityScoreTotal,
  computeMaxHpAtLevel,
  isStandardArrayDistribution,
  safeParseInt,
} from "../utils/calculations";
import {
  loadCharacterSheet,
  loadPlayCharacterSheet,
  saveCharacterSheet,
  savePlayCharacterSheet,
} from "../services/characterSheet.service";
import { getClass } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { getClassCreationConfig } from "../data/classCreation";
import { getRace } from "../data/races";
import {
  buildCreationLoadout,
  getInitialClassEquipmentSelections,
} from "../utils/creationEquipment";
import {
  getStartingSpellLimits,
  normalizeCreationSpellSelection,
  toggleStartingSpell,
} from "../utils/creationSpells";
import { subscribe } from "../../../shared/realtime/centrifugoClient";

// ── State ────────────────────────────────────────────────────────────────────

type State = {
  sheet: CharacterSheet;
  loading: boolean;
  saving: boolean;
  isDirty: boolean;
  loadError: string | null;
  saveError: string | null;
  remoteId: string | null;
  importError: string | null;
  playSessionId: string | null;
  playCampaignId: string | null;
  playPlayerUserId: string | null;
};

const initialState: State = {
  sheet: INITIAL_SHEET,
  loading: false,
  saving: false,
  isDirty: false,
  loadError: null,
  saveError: null,
  remoteId: null,
  importError: null,
  playSessionId: null,
  playCampaignId: null,
  playPlayerUserId: null,
};

// ── Actions ───────────────────────────────────────────────────────────────────

type Action =
  | { type: "load_start" }
  | {
      type: "load_success";
      sheet: CharacterSheet;
      id: string | null;
      playSessionId?: string | null;
      playCampaignId?: string | null;
      playPlayerUserId?: string | null;
    }
  | { type: "load_fail"; error: string }
  | { type: "update_sheet"; updater: (s: CharacterSheet) => CharacterSheet }
  | { type: "saving_start" }
  | { type: "saving_success"; id: string }
  | { type: "saving_fail"; error: string }
  | { type: "import_success"; sheet: CharacterSheet }
  | { type: "import_fail"; error: string }
  | { type: "reset" };

// ── Reducer ───────────────────────────────────────────────────────────────────

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "load_start":
      return { ...state, loading: true, loadError: null };
    case "load_success":
      return {
        ...state,
        loading: false,
        sheet: action.sheet,
        remoteId: action.id,
        isDirty: false,
        playSessionId: action.playSessionId ?? null,
        playCampaignId: action.playCampaignId ?? null,
        playPlayerUserId: action.playPlayerUserId ?? null,
      };
    case "load_fail":
      return { ...state, loading: false, loadError: action.error };
    case "update_sheet":
      return { ...state, sheet: action.updater(state.sheet), isDirty: true };
    case "saving_start":
      return { ...state, saving: true, saveError: null };
    case "saving_success":
      return { ...state, saving: false, isDirty: false, remoteId: action.id, saveError: null };
    case "saving_fail":
      return { ...state, saving: false, saveError: action.error };
    case "import_success":
      return { ...state, sheet: action.sheet, isDirty: true, importError: null };
    case "import_fail":
      return { ...state, importError: action.error };
    case "reset":
      return {
        ...initialState,
        remoteId: state.remoteId,
        playSessionId: state.playSessionId,
        playCampaignId: state.playCampaignId,
        playPlayerUserId: state.playPlayerUserId,
      };
    default:
      return state;
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────────

const createEmptySpellcasting = (ability: AbilityName = "intelligence"): SpellcastingData => ({
  ability,
  slots: Object.fromEntries(Array.from({ length: 9 }, (_, i) => [i + 1, { max: 0, used: 0 }])),
  spells: [],
});

const clampAbilityScore = (value: number) =>
  Math.max(ABILITY_SCORE_MIN, Math.min(ABILITY_SCORE_MAX, value));

const ABILITY_ORDER: AbilityName[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

const EMPTY_SAVES: CharacterSheet["savingThrowProficiencies"] = {
  strength: false,
  dexterity: false,
  constitution: false,
  intelligence: false,
  wisdom: false,
  charisma: false,
};

const applyRaceBonusesToAbilities = (
  abilities: CharacterSheet["abilities"],
  raceName: string,
) => {
  const race = getRace(raceName);
  if (!race) return { ...abilities };
  const next = { ...abilities };
  for (const [key, bonus] of Object.entries(race.abilityBonuses)) {
    const abilityKey = key as AbilityName;
    next[abilityKey] = clampAbilityScore((next[abilityKey] ?? 0) + (bonus ?? 0));
  }
  return next;
};

const stripRaceBonusesFromAbilities = (
  abilities: CharacterSheet["abilities"],
  raceName: string,
) => {
  const race = getRace(raceName);
  if (!race) return { ...abilities };
  const next = { ...abilities };
  for (const [key, bonus] of Object.entries(race.abilityBonuses)) {
    const abilityKey = key as AbilityName;
    next[abilityKey] = clampAbilityScore((next[abilityKey] ?? 0) - (bonus ?? 0));
  }
  return next;
};

const applyRaceBonusSwap = (
  abilities: CharacterSheet["abilities"],
  previousRaceName: string,
  nextRaceName: string,
) => applyRaceBonusesToAbilities(
  stripRaceBonusesFromAbilities(abilities, previousRaceName),
  nextRaceName,
);

const buildCreationSkillProficiencies = (
  current: CharacterSheet["skillProficiencies"],
  backgroundName: string,
  classChoices: SkillName[],
) => {
  const next = { ...current };
  for (const key of Object.keys(next) as SkillName[]) next[key] = 0;
  const bg = getBackground(backgroundName);
  bg?.skillProficiencies.forEach((skill) => { next[skill] = 1; });
  classChoices.forEach((skill) => { if (next[skill] === 0) next[skill] = 1; });
  return next;
};

const deriveLanguages = (raceName: string, backgroundName: string): string[] => {
  const race = getRace(raceName);
  const background = getBackground(backgroundName);
  return [...new Set([...(race?.languages ?? []), ...(background?.languages ?? [])])];
};

const buildCreationSpellcasting = (
  className: string,
  spellcastingAbility: AbilityName | null,
  abilities: CharacterSheet["abilities"],
  level: number,
  current: SpellcastingData | null = null,
) => {
  if (!spellcastingAbility) return null;
  const base: SpellcastingData = current
    ? {
        ...current,
        ability: spellcastingAbility,
        slots: { ...createEmptySpellcasting(spellcastingAbility).slots, ...current.slots },
      }
    : createEmptySpellcasting(spellcastingAbility);
  const normalized = normalizeCreationSpellSelection(base, className, abilities, level);
  if (!normalized) return { ...base, ability: spellcastingAbility };
  const limits = getStartingSpellLimits(className, abilities, level);
  if (!limits) return normalized;
  return {
    ...normalized,
    ability: spellcastingAbility,
    slots: {
      ...normalized.slots,
      1: { max: limits.levelOneSlots, used: Math.min(normalized.slots[1]?.used ?? 0, limits.levelOneSlots) },
    },
  };
};

const normalizeCreationAfterClassChange = (sheet: CharacterSheet, className: string): CharacterSheet => {
  const cls = getClass(className);
  const classEquipmentSelections = getInitialClassEquipmentSelections(className);
  const loadout = buildCreationLoadout(className, sheet.background, classEquipmentSelections);
  if (!cls) {
    return {
      ...sheet,
      class: className,
      classSkillChoices: [],
      classEquipmentSelections,
      skillProficiencies: buildCreationSkillProficiencies(sheet.skillProficiencies, sheet.background, []),
      savingThrowProficiencies: { ...EMPTY_SAVES },
      armorProficiencies: [],
      weaponProficiencies: [],
      hitDiceType: "",
      hitDiceTotal: sheet.level,
      hitDiceRemaining: sheet.level,
      maxHP: 0,
      currentHP: 0,
      spellcasting: null,
      inventory: loadout.inventory,
      currency: loadout.currency,
      equippedArmor: loadout.equippedArmor,
      equippedShield: loadout.equippedShield,
    };
  }

  const filteredChoices = sheet.classSkillChoices.filter((skill) => cls.skillChoices.includes(skill));
  const trimmedChoices = filteredChoices.slice(0, cls.skillCount);
  const savingThrowProficiencies = { ...EMPTY_SAVES };
  cls.savingThrows.forEach((ability) => { savingThrowProficiencies[ability] = true; });
  const skillProficiencies = buildCreationSkillProficiencies(sheet.skillProficiencies, sheet.background, trimmedChoices);
  const maxHP = computeMaxHpAtLevel(cls.hitDice, sheet.level, sheet.abilities.constitution);

  return {
    ...sheet,
    class: className,
    classSkillChoices: trimmedChoices,
    classEquipmentSelections,
    skillProficiencies,
    savingThrowProficiencies,
    armorProficiencies: [...cls.armorProficiencies],
    weaponProficiencies: [...cls.weaponProficiencies],
    toolProficiencies: [...(getBackground(sheet.background)?.toolProficiencies ?? [])],
    languages: deriveLanguages(sheet.race, sheet.background),
    hitDiceType: cls.hitDice,
    hitDiceTotal: sheet.level,
    hitDiceRemaining: sheet.level,
    maxHP,
    currentHP: maxHP,
    spellcasting: buildCreationSpellcasting(className, cls.spellcastingAbility, sheet.abilities, sheet.level),
    inventory: loadout.inventory,
    currency: loadout.currency,
    equippedArmor: loadout.equippedArmor,
    equippedShield: loadout.equippedShield,
  };
};

const normalizeCreationAfterBackgroundChange = (sheet: CharacterSheet, backgroundName: string): CharacterSheet => {
  const bg = getBackground(backgroundName);
  const cls = getClass(sheet.class);
  const classChoices = sheet.classSkillChoices.filter((skill) => cls?.skillChoices.includes(skill) ?? true);
  const trimmedChoices = cls ? classChoices.slice(0, cls.skillCount) : [];
  const skillProficiencies = buildCreationSkillProficiencies(sheet.skillProficiencies, backgroundName, trimmedChoices);
  const loadout = buildCreationLoadout(sheet.class, backgroundName, sheet.classEquipmentSelections);

  return {
    ...sheet,
    background: backgroundName,
    classSkillChoices: trimmedChoices,
    skillProficiencies,
    toolProficiencies: [...(bg?.toolProficiencies ?? [])],
    languages: deriveLanguages(sheet.race, backgroundName),
    inventory: loadout.inventory,
    currency: loadout.currency,
    equippedArmor: loadout.equippedArmor,
    equippedShield: loadout.equippedShield,
  };
};

const normalizeCreationAfterRaceChange = (sheet: CharacterSheet, raceName: string): CharacterSheet => {
  const race = getRace(raceName);
  const abilities = applyRaceBonusSwap(sheet.abilities, sheet.race, raceName);
  const cls = getClass(sheet.class);
  const maxHP = cls ? computeMaxHpAtLevel(cls.hitDice, sheet.level, abilities.constitution) : sheet.maxHP;
  return {
    ...sheet,
    race: raceName,
    speed: race?.speed ?? 0,
    abilities,
    maxHP,
    currentHP: cls ? maxHP : sheet.currentHP,
    spellcasting: normalizeCreationSpellSelection(sheet.spellcasting, sheet.class, abilities, sheet.level),
    languages: deriveLanguages(raceName, sheet.background),
  };
};

type UseCharacterSheetOptions = {
  playPlayerUserId?: string | null;
  canEditPlay?: boolean;
};

export const useCharacterSheet = (
  partyId?: string | null,
  mode: CharacterSheetMode = "play",
  options: UseCharacterSheetOptions = {},
) => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const importRef = useRef<HTMLInputElement>(null);
  const playEventVersionRef = useRef(0);
  const playPlayerUserId = options.playPlayerUserId ?? null;
  const canEditPlay = options.canEditPlay ?? false;
  const canMutate = mode !== "play" || canEditPlay;

  const update = (updater: (s: CharacterSheet) => CharacterSheet) =>
    dispatch({ type: "update_sheet", updater });

  const guardedUpdate = (updater: (s: CharacterSheet) => CharacterSheet) =>
    update((sheet) => (canMutate ? updater(sheet) : sheet));

  // ── API load ────────────────────────────────────────────────────────────────

  const loadSheet = useCallback(async () => {
    if (!partyId) return;
    dispatch({ type: "load_start" });
    try {
      if (mode === "play") {
        if (!playPlayerUserId) {
          throw new Error("Missing player for play sheet.");
        }
        const result = await loadPlayCharacterSheet(partyId, playPlayerUserId, !canEditPlay);
        dispatch({
          type: "load_success",
          sheet: result.sheet,
          id: result.id,
          playSessionId: result.sessionId,
          playCampaignId: result.campaignId,
          playPlayerUserId: playPlayerUserId,
        });
        return;
      }

      const result = await loadCharacterSheet(partyId);
      dispatch({ type: "load_success", sheet: result.sheet, id: result.id });
    } catch (err: unknown) {
      dispatch({ type: "load_fail", error: (err as { message?: string })?.message ?? "Failed to load" });
    }
  }, [partyId, mode, playPlayerUserId, canEditPlay]);

  useEffect(() => {
    void loadSheet();
  }, [loadSheet]);

  useEffect(() => {
    if (mode !== "play" || canEditPlay || !state.playCampaignId || !state.playSessionId || !state.playPlayerUserId) {
      return;
    }
    playEventVersionRef.current = 0;
    const unsubscribe = subscribe(`campaign:${state.playCampaignId}`, {
      onPublication: (message) => {
        if (!message || typeof message !== "object") return;
        const data = message as {
          type?: string;
          version?: number;
          payload?: { sessionId?: string; playerUserId?: string };
        };
        if (
          data.type === "session_state_updated" &&
          data.payload?.sessionId === state.playSessionId &&
          data.payload?.playerUserId === state.playPlayerUserId
        ) {
          if (
            typeof data.version === "number" &&
            data.version <= playEventVersionRef.current
          ) {
            return;
          }
          if (typeof data.version === "number") {
            playEventVersionRef.current = data.version;
          }
          void loadSheet();
        }
      },
    });
    return () => {
      unsubscribe();
    };
  }, [mode, canEditPlay, state.playCampaignId, state.playPlayerUserId, state.playSessionId, loadSheet]);

  // ── API save ────────────────────────────────────────────────────────────────

  const save = async () => {
    if (!partyId) return;
    if (mode === "play") {
      if (!canEditPlay || !state.playSessionId || !state.playPlayerUserId) return;
      dispatch({ type: "saving_start" });
      try {
        const id = await savePlayCharacterSheet(state.playSessionId, state.playPlayerUserId, state.sheet);
        dispatch({ type: "saving_success", id });
      } catch (err: unknown) {
        dispatch({ type: "saving_fail", error: (err as { message?: string })?.message ?? "Failed to save" });
      }
      return;
    }
    if (mode === "creation") {
      const baseAbilities = stripRaceBonusesFromAbilities(state.sheet.abilities, state.sheet.race);
      if (!isStandardArrayDistribution(baseAbilities)) {
        dispatch({
          type: "saving_fail",
          error: `Ability scores must follow Standard Array (${STANDARD_ARRAY.join(", ")}).`,
        });
        return;
      }
    } else {
      const abilityTotal = computeAbilityScoreTotal(state.sheet.abilities);
      if (abilityTotal !== ABILITY_SCORE_POOL) {
        const diff = ABILITY_SCORE_POOL - abilityTotal;
        dispatch({
          type: "saving_fail",
          error:
            diff > 0
              ? `Ability scores must total ${ABILITY_SCORE_POOL} (remaining: ${diff}).`
              : `Ability scores must total ${ABILITY_SCORE_POOL} (over by ${Math.abs(diff)}).`,
        });
        return;
      }
    }

    dispatch({ type: "saving_start" });
    try {
      const id = await saveCharacterSheet(partyId, state.sheet, state.remoteId ?? undefined);
      dispatch({ type: "saving_success", id });
    } catch (err: unknown) {
      dispatch({ type: "saving_fail", error: (err as { message?: string })?.message ?? "Failed to save" });
    }
  };

  // ── Generic field setter ────────────────────────────────────────────────────

  const set = <K extends keyof CharacterSheet>(key: K, value: CharacterSheet[K]) =>
    guardedUpdate((s) => {
      if (mode === "creation" && key === "speed") return s;
      if (mode === "creation" && key === "level") {
        const lvl = Math.max(1, safeParseInt(String(value), 1));
        const cls = getClass(s.class);
        if (!cls) return { ...s, level: lvl };
        const maxHP = computeMaxHpAtLevel(cls.hitDice, lvl, s.abilities.constitution);
        const spellcasting = normalizeCreationSpellSelection(s.spellcasting, s.class, s.abilities, lvl);
        return {
          ...s,
          level: lvl,
          hitDiceTotal: lvl,
          hitDiceRemaining: lvl,
          maxHP,
          currentHP: maxHP,
          spellcasting,
        };
      }
      return { ...s, [key]: value };
    });

  // ── Abilities ───────────────────────────────────────────────────────────────

  const setAbility = (a: AbilityName, v: number) =>
    guardedUpdate((s) => {
      if (mode === "creation") {
        if (!STANDARD_ARRAY.includes(v as (typeof STANDARD_ARRAY)[number])) return s;
        const baseAbilities = stripRaceBonusesFromAbilities(s.abilities, s.race);
        const previousValue = baseAbilities[a];
        const swappedAbility = ABILITY_ORDER.find((ability) => ability !== a && baseAbilities[ability] === v);
        const nextBase = { ...baseAbilities, [a]: v };
        if (swappedAbility) nextBase[swappedAbility] = previousValue;
        const nextAbilities = applyRaceBonusesToAbilities(nextBase, s.race);
        const cls = getClass(s.class);
        if (!cls) {
          return {
            ...s,
            abilities: nextAbilities,
            spellcasting: normalizeCreationSpellSelection(s.spellcasting, s.class, nextAbilities, s.level),
          };
        }
        const maxHP = computeMaxHpAtLevel(cls.hitDice, s.level, nextAbilities.constitution);
        return {
          ...s,
          abilities: nextAbilities,
          maxHP,
          currentHP: maxHP,
          spellcasting: normalizeCreationSpellSelection(s.spellcasting, s.class, nextAbilities, s.level),
        };
      }
      return {
        ...s,
        abilities: {
          ...s.abilities,
          [a]: clampAbilityScore(v),
        },
      };
    });

  // ── Saves & Skills ──────────────────────────────────────────────────────────

  const toggleSaveProf = (a: AbilityName) =>
    guardedUpdate((s) => mode === "creation"
      ? s
      : ({ ...s, savingThrowProficiencies: { ...s.savingThrowProficiencies, [a]: !s.savingThrowProficiencies[a] } }));

  const cycleSkillProf = (sk: SkillName) =>
    guardedUpdate((s) => {
      if (mode === "creation") return s;
      const order: ProficiencyLevel[] = [0, 0.5, 1, 2];
      const next = order[(order.indexOf(s.skillProficiencies[sk]) + 1) % order.length];
      return { ...s, skillProficiencies: { ...s.skillProficiencies, [sk]: next } };
    });

  // ── HP ──────────────────────────────────────────────────────────────────────

  const setCurrentHP = (v: number) =>
    guardedUpdate((s) => ({ ...s, currentHP: clampHP(v, s.maxHP) }));
  const setMaxHP = (v: number) => {
    const m = Math.max(0, v);
    guardedUpdate((s) => ({ ...s, maxHP: m, currentHP: Math.min(s.currentHP, m) }));
  };
  const adjustHP = (delta: number) =>
    guardedUpdate((s) => ({ ...s, currentHP: clampHP(s.currentHP + delta, s.maxHP) }));

  // ── Death Saves ─────────────────────────────────────────────────────────────

  const setDeathSave = (type: "successes" | "failures", v: number) =>
    guardedUpdate((s) => ({ ...s, deathSaves: { ...s.deathSaves, [type]: Math.max(0, Math.min(3, v)) } }));

  // ── Conditions ──────────────────────────────────────────────────────────────

  const toggleCondition = (c: ConditionName) =>
    guardedUpdate((s) => ({ ...s, conditions: { ...s.conditions, [c]: !s.conditions[c] } }));

  // ── Hit Dice ────────────────────────────────────────────────────────────────

  const useHitDie = () =>
    guardedUpdate((s) => ({ ...s, hitDiceRemaining: Math.max(0, s.hitDiceRemaining - 1) }));
  const longRest = () =>
    guardedUpdate((s) => ({ ...s, hitDiceRemaining: s.hitDiceTotal, currentHP: s.maxHP }));

  // ── Armor ───────────────────────────────────────────────────────────────────

  const selectArmor = (name: string) => {
    const preset = ARMOR_PRESETS.find((a) => a.name === name);
    if (preset) set("equippedArmor", { ...preset });
  };
  const toggleShield = () =>
    guardedUpdate((s) => ({ ...s, equippedShield: s.equippedShield ? null : { name: "Shield", bonus: 2 } }));

  // ── Weapons ─────────────────────────────────────────────────────────────────

  const addWeapon = () =>
    guardedUpdate((s) => ({
      ...s,
      weapons: [...s.weapons, { id: nanoid(), name: "", ability: "strength" as AbilityName, damageDice: "1d6", damageType: "slashing", proficient: true, magicBonus: 0, properties: "", range: "" }],
    }));
  const removeWeapon = (id: string) =>
    guardedUpdate((s) => ({ ...s, weapons: s.weapons.filter((w) => w.id !== id) }));
  const updateWeapon = <K extends keyof Weapon>(id: string, key: K, value: Weapon[K]) =>
    guardedUpdate((s) => ({ ...s, weapons: s.weapons.map((w) => (w.id === id ? { ...w, [key]: value } : w)) }));

  // ── Inventory ───────────────────────────────────────────────────────────────

  const addItem = () =>
    guardedUpdate((s) => ({ ...s, inventory: [...s.inventory, { id: nanoid(), name: "", quantity: 1, weight: 0, notes: "" }] }));
  const removeItem = (id: string) =>
    guardedUpdate((s) => ({ ...s, inventory: s.inventory.filter((i) => i.id !== id) }));
  const updateItem = <K extends keyof InventoryItem>(id: string, key: K, value: InventoryItem[K]) =>
    guardedUpdate((s) => ({ ...s, inventory: s.inventory.map((i) => (i.id === id ? { ...i, [key]: value } : i)) }));
  const setCurrency = (coin: keyof CharacterSheet["currency"], v: number) =>
    guardedUpdate((s) => ({ ...s, currency: { ...s.currency, [coin]: Math.max(0, v) } }));

  // ── Spellcasting ────────────────────────────────────────────────────────────

  const enableSpellcasting = () => set("spellcasting", createEmptySpellcasting());
  const disableSpellcasting = () => set("spellcasting", null);
  const setSpellAbility = (a: AbilityName) =>
    guardedUpdate((s) => s.spellcasting ? { ...s, spellcasting: { ...s.spellcasting, ability: a } } : s);
  const setSpellSlot = (lvl: number, key: "max" | "used", v: number) =>
    guardedUpdate((s) => {
      if (!s.spellcasting) return s;
      const slot = s.spellcasting.slots[lvl] ?? { max: 0, used: 0 };
      const next = { ...slot, [key]: Math.max(0, key === "used" ? Math.min(v, slot.max) : v) };
      if (key === "max" && next.used > next.max) next.used = next.max;
      return { ...s, spellcasting: { ...s.spellcasting, slots: { ...s.spellcasting.slots, [lvl]: next } } };
    });
  const addSpell = () =>
    guardedUpdate((s) => {
      if (!s.spellcasting) return s;
      return { ...s, spellcasting: { ...s.spellcasting, spells: [...s.spellcasting.spells, { id: nanoid(), name: "", level: 0, school: "Evocation", prepared: false, notes: "" }] } };
    });
  const removeSpell = (id: string) =>
    guardedUpdate((s) => {
      if (!s.spellcasting) return s;
      return { ...s, spellcasting: { ...s.spellcasting, spells: s.spellcasting.spells.filter((sp) => sp.id !== id) } };
    });
  const updateSpell = <K extends keyof Spell>(id: string, key: K, value: Spell[K]) =>
    guardedUpdate((s) => {
      if (!s.spellcasting) return s;
      return { ...s, spellcasting: { ...s.spellcasting, spells: s.spellcasting.spells.map((sp) => (sp.id === id ? { ...sp, [key]: value } : sp)) } };
    });

  // ── Tags ────────────────────────────────────────────────────────────────────

  type TagField = "languages" | "toolProficiencies" | "weaponProficiencies" | "armorProficiencies";
  const addTag = (field: TagField, value: string) =>
    guardedUpdate((s) => ({ ...s, [field]: [...s[field], value] }));
  const removeTag = (field: TagField, idx: number) =>
    guardedUpdate((s) => ({ ...s, [field]: s[field].filter((_: string, i: number) => i !== idx) }));

  // ── Class / Background / Race ───────────────────────────────────────────────

  const selectClass = (name: string) => {
    if (mode === "creation") {
      update((s) => normalizeCreationAfterClassChange(s, name));
      return;
    }
    const cls = getClass(name);
    if (!cls) return set("class", name);
    guardedUpdate((s) => ({ ...s, class: name, hitDiceType: cls.hitDice }));
  };

  const selectBackground = (name: string) => {
    if (mode === "creation") {
      update((s) => normalizeCreationAfterBackgroundChange(s, name));
      return;
    }
    const bg = getBackground(name);
    if (!bg) return set("background", name);
    guardedUpdate((s) => ({ ...s, background: name }));
  };

  const selectRace = (name: string) => {
    guardedUpdate((s) => {
      if (mode === "creation") return normalizeCreationAfterRaceChange(s, name);
      const race = getRace(name);
      return { ...s, race: name, speed: race?.speed ?? 0, abilities: applyRaceBonusSwap(s.abilities, s.race, name) };
    });
  };

  const selectClassEquipment = (groupId: string, optionId: string) =>
    guardedUpdate((s) => {
      if (mode !== "creation") return s;
      const nextSelections = { ...s.classEquipmentSelections, [groupId]: optionId };
      const loadout = buildCreationLoadout(s.class, s.background, nextSelections);
      return {
        ...s,
        classEquipmentSelections: nextSelections,
        inventory: loadout.inventory,
        currency: loadout.currency,
        equippedArmor: loadout.equippedArmor,
        equippedShield: loadout.equippedShield,
      };
    });

  const pickClassSkill = (skill: SkillName) =>
    guardedUpdate((s) => {
      const cls = getClass(s.class);
      if (!cls) return s;
      if (!cls.skillChoices.includes(skill)) return s;
      const bgSkills = new Set(getBackground(s.background)?.skillProficiencies ?? []);
      if (bgSkills.has(skill)) return s;
      const isChosen = s.classSkillChoices.includes(skill);
      if (!isChosen && s.classSkillChoices.length >= cls.skillCount) return s;
      const nextChoices = isChosen
        ? s.classSkillChoices.filter((sk) => sk !== skill)
        : [...s.classSkillChoices, skill];
      if (mode === "creation") {
        const skills = buildCreationSkillProficiencies(s.skillProficiencies, s.background, nextChoices);
        return { ...s, classSkillChoices: nextChoices, skillProficiencies: skills };
      }
      const skills = { ...s.skillProficiencies };
      if (isChosen) { if (skills[skill] === 1) skills[skill] = 0; }
      else { if (skills[skill] === 0) skills[skill] = 1; }
      return { ...s, classSkillChoices: nextChoices, skillProficiencies: skills };
    });

  const toggleCreationSpellSelection = (spellName: string) =>
    guardedUpdate((s) => {
      if (mode !== "creation" || !s.spellcasting || !getClassCreationConfig(s.class)?.startingSpells) {
        return s;
      }
      const nextSpellcasting = toggleStartingSpell(
        s.spellcasting,
        s.class,
        s.abilities,
        s.level,
        spellName,
      );
      return nextSpellcasting ? { ...s, spellcasting: nextSpellcasting } : s;
    });

  // ── Export / Import ─────────────────────────────────────────────────────────

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(state.sheet, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.sheet.name || "character"}-sheet.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
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
    // State
    mode,
    sheet: state.sheet,
    loading: state.loading,
    saving: state.saving,
    isDirty: state.isDirty,
    loadError: state.loadError,
    saveError: state.saveError,
    remoteId: state.remoteId,
    importError: state.importError,
    importRef,
    // API
    save,
    // Handlers
    set, setAbility,
    toggleSaveProf, cycleSkillProf,
    setCurrentHP, setMaxHP, adjustHP,
    setDeathSave, toggleCondition,
    useHitDie, longRest,
    selectArmor, toggleShield,
    addWeapon, removeWeapon, updateWeapon,
    addItem, removeItem, updateItem, setCurrency,
    enableSpellcasting, disableSpellcasting, setSpellAbility, setSpellSlot,
    addSpell, removeSpell, updateSpell,
    addTag, removeTag,
    selectClass, selectBackground, selectRace, selectClassEquipment, pickClassSkill,
    toggleCreationSpellSelection,
    handleExport, handleImport, resetSheet,
    safeParseInt,
  };
};

export type SheetActions = ReturnType<typeof useCharacterSheet>;
