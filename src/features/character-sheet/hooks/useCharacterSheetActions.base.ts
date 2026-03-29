import { nanoid } from "nanoid";
import type {
  AbilityName,
  CharacterSheet,
  ConditionName,
  InventoryItem,
  ProficiencyLevel,
  SkillName,
  Spell,
  Weapon,
} from "../model/characterSheet.types";
import { ARMOR_PRESETS } from "../constants";
import { clampHP } from "../utils/calculations";
import {
  buildCreationArmorOptions,
  hasCreationShieldInInventory,
  syncCreationInventoryLoadoutState,
} from "../utils/creationEquipment";
import {
  findCreationItemByCanonicalKey,
  getCreationCatalogItemsSorted,
  getCreationItemCatalog,
} from "../utils/creationItemCatalog";
import {
  getCatalogSpellOptions,
  selectCatalogSpellForSheet,
} from "../utils/creationSpells";
import { createEmptySpellcasting } from "./useCharacterSheet.creation";
import { fromCopper, toCopper } from "../../../shared/utils/money";

type GuardedUpdate = (updater: (sheet: CharacterSheet) => CharacterSheet) => void;
type SetField = <K extends keyof CharacterSheet>(key: K, value: CharacterSheet[K]) => void;

export const createBaseSheetActions = (
  guardedUpdate: GuardedUpdate,
  set: SetField,
  mode: "creation" | "play",
  options: {
    allowCreationEditing?: boolean;
    campaignId?: string | null;
  } = {},
) => {
  const allowCreationEditing = options.allowCreationEditing ?? false;
  const campaignId = options.campaignId ?? null;

  const setCurrentHP = (value: number) =>
    guardedUpdate((sheet) => ({ ...sheet, currentHP: clampHP(value, sheet.maxHP) }));

  const setMaxHP = (value: number) => {
    const nextMax = Math.max(0, value);
    guardedUpdate((sheet) => ({ ...sheet, maxHP: nextMax, currentHP: Math.min(sheet.currentHP, nextMax) }));
  };

  const adjustHP = (delta: number) =>
    guardedUpdate((sheet) => ({ ...sheet, currentHP: clampHP(sheet.currentHP + delta, sheet.maxHP) }));

  const toggleSaveProf = (ability: AbilityName) =>
    guardedUpdate((sheet) => mode === "creation" && !allowCreationEditing
      ? sheet
      : ({
          ...sheet,
          savingThrowProficiencies: {
            ...sheet.savingThrowProficiencies,
            [ability]: !sheet.savingThrowProficiencies[ability],
          },
        }));

  const cycleSkillProf = (skill: SkillName) =>
    guardedUpdate((sheet) => {
      if (mode === "creation" && !allowCreationEditing) return sheet;
      const order: ProficiencyLevel[] = [0, 0.5, 1, 2];
      const next = order[(order.indexOf(sheet.skillProficiencies[skill]) + 1) % order.length];
      return {
        ...sheet,
        skillProficiencies: { ...sheet.skillProficiencies, [skill]: next },
      };
    });

  const setDeathSave = (type: "successes" | "failures", value: number) =>
    guardedUpdate((sheet) => ({
      ...sheet,
      deathSaves: {
        ...sheet.deathSaves,
        [type]: Math.max(0, Math.min(3, value)),
      },
    }));

  const toggleCondition = (condition: ConditionName) =>
    guardedUpdate((sheet) => ({
      ...sheet,
      conditions: { ...sheet.conditions, [condition]: !sheet.conditions[condition] },
    }));

  const useHitDie = () =>
    guardedUpdate((sheet) => ({ ...sheet, hitDiceRemaining: Math.max(0, sheet.hitDiceRemaining - 1) }));

  const longRest = () =>
    guardedUpdate((sheet) => ({ ...sheet, hitDiceRemaining: sheet.hitDiceTotal, currentHP: sheet.maxHP }));

  const selectArmor = (value: string) => {
    if (mode === "creation") {
      guardedUpdate((sheet) => {
        const armorOptions = buildCreationArmorOptions(sheet.inventory);
        const selectedArmor = armorOptions.find((option) => option.value === value) ?? null;
        return {
          ...sheet,
          equippedArmorItemId: selectedArmor?.value ?? null,
          equippedArmor:
            selectedArmor?.armor ??
            ({ ...ARMOR_PRESETS.find((entry) => entry.name === "None")! }),
        };
      });
      return;
    }

    const preset = ARMOR_PRESETS.find((entry) => entry.name === value);
    if (preset) set("equippedArmor", { ...preset });
  };

  const toggleShield = () =>
    guardedUpdate((sheet) => {
      if (mode === "creation" && !hasCreationShieldInInventory(sheet.inventory)) {
        return sheet;
      }
      return {
        ...sheet,
        equippedShield: sheet.equippedShield ? null : { name: "Shield", bonus: 2 },
      };
    });

  const addWeapon = () =>
    guardedUpdate((sheet) => ({
      ...sheet,
      weapons: [
        ...sheet.weapons,
        {
          id: nanoid(),
          name: "",
          ability: "strength" as AbilityName,
          damageDice: "1d6",
          damageType: "slashing",
          proficient: true,
          magicBonus: 0,
          properties: "",
          range: "",
          rangeType: null,
        },
      ],
    }));

  const removeWeapon = (id: string) =>
    guardedUpdate((sheet) => ({ ...sheet, weapons: sheet.weapons.filter((weapon) => weapon.id !== id) }));

  const updateWeapon = <K extends keyof Weapon>(id: string, key: K, value: Weapon[K]) =>
    guardedUpdate((sheet) => ({
      ...sheet,
      weapons: sheet.weapons.map((weapon) => (weapon.id === id ? { ...weapon, [key]: value } : weapon)),
    }));

  const addItem = () =>
    guardedUpdate((sheet) => {
      const firstCatalogItem =
        mode === "creation" ? getCreationCatalogItemsSorted(getCreationItemCatalog())[0] ?? null : null;
      const nextSheet = {
        ...sheet,
        inventory: [
          ...sheet.inventory,
          {
            id: nanoid(),
            name: firstCatalogItem?.name ?? "",
            quantity: 1,
            weight: firstCatalogItem?.weight ?? 0,
            notes: "",
            canonicalKey: firstCatalogItem?.canonicalKey ?? null,
            campaignItemId: firstCatalogItem?.campaignItemId ?? null,
            baseItemId: firstCatalogItem?.baseItemId ?? null,
          },
        ],
      };
      return mode === "creation" ? syncCreationInventoryLoadoutState(nextSheet) : nextSheet;
    });

  const removeItem = (id: string) =>
    guardedUpdate((sheet) => {
      const nextSheet = {
        ...sheet,
        inventory: sheet.inventory.filter((item) => item.id !== id),
      };
      return mode === "creation" ? syncCreationInventoryLoadoutState(nextSheet) : nextSheet;
    });

  const updateItem = <K extends keyof InventoryItem>(id: string, key: K, value: InventoryItem[K]) =>
    guardedUpdate((sheet) => {
      const nextSheet = {
        ...sheet,
        inventory: sheet.inventory.map((item) => (item.id === id ? { ...item, [key]: value } : item)),
      };
      return mode === "creation" ? syncCreationInventoryLoadoutState(nextSheet) : nextSheet;
    });

  const selectInventoryCatalogItem = (id: string, canonicalKey: string) =>
    guardedUpdate((sheet) => {
      const catalogItem = findCreationItemByCanonicalKey(canonicalKey, getCreationItemCatalog());
      if (!catalogItem) {
        return sheet;
      }

      const nextSheet = {
        ...sheet,
        inventory: sheet.inventory.map((item) =>
          item.id === id
            ? {
                ...item,
                name: catalogItem.name,
                weight: catalogItem.weight,
                canonicalKey: catalogItem.canonicalKey,
                campaignItemId: catalogItem.campaignItemId,
                baseItemId: catalogItem.baseItemId,
              }
            : item,
        ),
      };
      return mode === "creation" ? syncCreationInventoryLoadoutState(nextSheet) : nextSheet;
    });

  const setCurrency = (coin: "cp" | "sp" | "ep" | "gp" | "pp", value: number) =>
    guardedUpdate((sheet) => {
      const nextCoins = fromCopper(sheet.currency.copperValue);
      nextCoins[coin] = Math.max(0, value);
      return {
        ...sheet,
        currency: {
          copperValue:
            toCopper(nextCoins.cp, "cp") +
            toCopper(nextCoins.sp, "sp") +
            toCopper(nextCoins.ep, "ep") +
            toCopper(nextCoins.gp, "gp") +
            toCopper(nextCoins.pp, "pp"),
        },
      };
    });

  const enableSpellcasting = () => set("spellcasting", createEmptySpellcasting());
  const disableSpellcasting = () => set("spellcasting", null);

  const setSpellAbility = (ability: AbilityName) =>
    guardedUpdate((sheet) => sheet.spellcasting
      ? { ...sheet, spellcasting: { ...sheet.spellcasting, ability } }
      : sheet);

  const setSpellSlot = (level: number, key: "max" | "used", value: number) =>
    guardedUpdate((sheet) => {
      if (!sheet.spellcasting) return sheet;
      const slot = sheet.spellcasting.slots[level] ?? { max: 0, used: 0 };
      const next = {
        ...slot,
        [key]: Math.max(0, key === "used" ? Math.min(value, slot.max) : value),
      };
      if (key === "max" && next.used > next.max) next.used = next.max;
      return {
        ...sheet,
        spellcasting: {
          ...sheet.spellcasting,
          slots: { ...sheet.spellcasting.slots, [level]: next },
        },
      };
    });

  const addSpell = () =>
    guardedUpdate((sheet) => {
      if (!sheet.spellcasting) return sheet;
      if (mode === "creation") {
        const firstCatalogSpell = getCatalogSpellOptions(sheet.class, campaignId)[0];
        if (!firstCatalogSpell) return sheet;
        const nextSpell = selectCatalogSpellForSheet(
          firstCatalogSpell.canonicalKey,
          sheet.class,
          sheet.spellcasting.mode,
          campaignId,
        );
        if (!nextSpell) return sheet;
        return {
          ...sheet,
          spellcasting: {
            ...sheet.spellcasting,
            spells: [...sheet.spellcasting.spells, nextSpell],
          },
        };
      }
      return {
        ...sheet,
        spellcasting: {
          ...sheet.spellcasting,
          spells: [
            ...sheet.spellcasting.spells,
            { id: nanoid(), name: "", level: 0, school: "Evocation", prepared: false, notes: "" },
          ],
        },
      };
    });

  const selectCatalogSpell = (id: string, canonicalKey: string) =>
    guardedUpdate((sheet) => {
      if (!sheet.spellcasting) return sheet;
      const existingSpell = sheet.spellcasting.spells.find((spell) => spell.id === id);
      if (!existingSpell) return sheet;

      const nextSpell = selectCatalogSpellForSheet(
        canonicalKey,
        sheet.class,
        sheet.spellcasting.mode,
        campaignId,
        existingSpell,
      );
      if (!nextSpell) return sheet;

      return {
        ...sheet,
        spellcasting: {
          ...sheet.spellcasting,
          spells: sheet.spellcasting.spells.map((spell) =>
            spell.id === id ? nextSpell : spell,
          ),
        },
      };
    });

  const removeSpell = (id: string) =>
    guardedUpdate((sheet) => {
      if (!sheet.spellcasting) return sheet;
      return {
        ...sheet,
        spellcasting: {
          ...sheet.spellcasting,
          spells: sheet.spellcasting.spells.filter((spell) => spell.id !== id),
        },
      };
    });

  const updateSpell = <K extends keyof Spell>(id: string, key: K, value: Spell[K]) =>
    guardedUpdate((sheet) => {
      if (!sheet.spellcasting) return sheet;
      return {
        ...sheet,
        spellcasting: {
          ...sheet.spellcasting,
          spells: sheet.spellcasting.spells.map((spell) => (spell.id === id ? { ...spell, [key]: value } : spell)),
        },
      };
    });

  type TagField = "languages" | "toolProficiencies" | "weaponProficiencies" | "armorProficiencies";

  const addTag = (field: TagField, value: string) =>
    guardedUpdate((sheet) => ({ ...sheet, [field]: [...sheet[field], value] }));

  const removeTag = (field: TagField, index: number) =>
    guardedUpdate((sheet) => ({
      ...sheet,
      [field]: sheet[field].filter((_: string, entryIndex: number) => entryIndex !== index),
    }));

  return {
    setCurrentHP,
    setMaxHP,
    adjustHP,
    toggleSaveProf,
    cycleSkillProf,
    setDeathSave,
    toggleCondition,
    useHitDie,
    longRest,
    selectArmor,
    toggleShield,
    addWeapon,
    removeWeapon,
    updateWeapon,
    addItem,
    removeItem,
    updateItem,
    selectInventoryCatalogItem,
    setCurrency,
    enableSpellcasting,
    disableSpellcasting,
    setSpellAbility,
    setSpellSlot,
    addSpell,
    selectCatalogSpell,
    removeSpell,
    updateSpell,
    addTag,
    removeTag,
  };
};
