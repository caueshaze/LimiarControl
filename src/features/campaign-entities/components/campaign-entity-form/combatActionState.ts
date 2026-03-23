import { type Dispatch, type SetStateAction } from "react";
import { type BaseSpell } from "../../../../entities/base-spell";
import {
  type CampaignEntityPayload,
  type CombatAction,
  type CombatActionKind,
} from "../../../../entities/campaign-entity";
import { type Item } from "../../../../entities/item";
import { createCombatAction, isDamageType } from "./constants";
import type { SpellLabelFn, WeaponLabelFn } from "./types";

type SetForm = Dispatch<SetStateAction<CampaignEntityPayload>>;

type SharedProps = {
  setForm: SetForm;
  weaponById: Map<string, Item>;
  spellByKey: Map<string, BaseSpell>;
  weaponLabel: WeaponLabelFn;
  spellLabel: SpellLabelFn;
};

export const createCombatActionFieldSetter =
  ({ setForm }: Pick<SharedProps, "setForm">) =>
  <K extends keyof CombatAction>(index: number, key: K, value: CombatAction[K]) => {
    setForm((prev) => ({
      ...prev,
      combatActions: prev.combatActions.map((action, actionIndex) =>
        actionIndex === index ? { ...action, [key]: value } : action,
      ),
    }));
  };

export const createCombatActionKindSetter =
  ({ setForm }: Pick<SharedProps, "setForm">) =>
  (index: number, kind: CombatActionKind) => {
    setForm((prev) => ({
      ...prev,
      combatActions: prev.combatActions.map((action, actionIndex) => {
        if (actionIndex !== index) {
          return action;
        }

        if (kind === "utility") {
          return { id: action.id, name: action.name, kind, description: action.description ?? "" };
        }

        if (kind === "weapon_attack") {
          return {
            id: action.id,
            name: action.name,
            kind,
            campaignItemId: action.campaignItemId ?? null,
            weaponCanonicalKey: action.weaponCanonicalKey ?? null,
            toHitBonus: action.toHitBonus ?? null,
            damageDice: action.damageDice ?? "",
            damageBonus: action.damageBonus ?? null,
            damageType: action.damageType ?? null,
            rangeMeters: action.rangeMeters ?? null,
            isMelee: action.isMelee ?? null,
            description: action.description ?? "",
          };
        }

        if (kind === "spell_attack") {
          return {
            id: action.id,
            name: action.name,
            kind,
            spellCanonicalKey: action.spellCanonicalKey ?? null,
            toHitBonus: action.toHitBonus ?? null,
            spellAttackBonus: action.spellAttackBonus ?? null,
            damageDice: action.damageDice ?? "",
            damageBonus: action.damageBonus ?? null,
            damageType: action.damageType ?? null,
            rangeMeters: action.rangeMeters ?? null,
            castAtLevel: action.castAtLevel ?? null,
            description: action.description ?? "",
          };
        }

        if (kind === "saving_throw") {
          return {
            id: action.id,
            name: action.name,
            kind,
            spellCanonicalKey: action.spellCanonicalKey ?? null,
            damageDice: action.damageDice ?? "",
            damageBonus: action.damageBonus ?? null,
            damageType: action.damageType ?? null,
            rangeMeters: action.rangeMeters ?? null,
            saveAbility: action.saveAbility ?? null,
            saveDc: action.saveDc ?? null,
            castAtLevel: action.castAtLevel ?? null,
            description: action.description ?? "",
          };
        }

        return {
          id: action.id,
          name: action.name,
          kind,
          spellCanonicalKey: action.spellCanonicalKey ?? null,
          healDice: action.healDice ?? "",
          healBonus: action.healBonus ?? null,
          castAtLevel: action.castAtLevel ?? null,
          description: action.description ?? "",
        };
      }),
    }));
  };

export const createWeaponCatalogActionSelector =
  ({ setForm, weaponById, weaponLabel }: Pick<SharedProps, "setForm" | "weaponById" | "weaponLabel">) =>
  (index: number, campaignItemId: string) => {
    const selectedWeapon = weaponById.get(campaignItemId);
    setForm((prev) => ({
      ...prev,
      combatActions: prev.combatActions.map((action, actionIndex) => {
        if (actionIndex !== index) {
          return action;
        }
        if (!selectedWeapon) {
          return {
            ...action,
            campaignItemId: campaignItemId || null,
            weaponCanonicalKey: null,
          };
        }
        return {
          ...action,
          campaignItemId: campaignItemId || null,
          weaponCanonicalKey: selectedWeapon.canonicalKeySnapshot ?? null,
          name: action.name.trim() || weaponLabel(selectedWeapon),
          damageDice: selectedWeapon.damageDice ?? "",
          damageType: isDamageType(selectedWeapon.damageType?.toLowerCase())
            ? selectedWeapon.damageType.toLowerCase()
            : null,
          rangeMeters: typeof selectedWeapon.rangeMeters === "number" ? selectedWeapon.rangeMeters : null,
          isMelee:
            selectedWeapon.weaponRangeType === "melee"
              ? true
              : selectedWeapon.weaponRangeType === "ranged"
                ? false
                : null,
        };
      }),
    }));
  };

export const createSpellCatalogActionSelector =
  ({ setForm, spellByKey, spellLabel }: Pick<SharedProps, "setForm" | "spellByKey" | "spellLabel">) =>
  (index: number, canonicalKey: string) => {
    const selectedSpell = spellByKey.get(canonicalKey);
    setForm((prev) => ({
      ...prev,
      combatActions: prev.combatActions.map((action, actionIndex) =>
        actionIndex === index
          ? {
              ...action,
              spellCanonicalKey: canonicalKey || null,
              name: action.name.trim() || (selectedSpell ? spellLabel(selectedSpell) : action.name),
            }
          : action,
      ),
    }));
  };

export const createCombatActionAdder =
  ({ setForm }: Pick<SharedProps, "setForm">) =>
  () => {
    setForm((prev) => ({
      ...prev,
      combatActions: [...prev.combatActions, createCombatAction()],
    }));
  };

export const createCombatActionRemover =
  ({ setForm }: Pick<SharedProps, "setForm">) =>
  (index: number) => {
    setForm((prev) => ({
      ...prev,
      combatActions: prev.combatActions.filter((_, actionIndex) => actionIndex !== index),
    }));
  };
