import type { CombatAction } from "./campaignEntity.types";

const withSign = (value: number | null | undefined) => {
  if (typeof value !== "number") {
    return null;
  }
  return value >= 0 ? `+${value}` : String(value);
};

export const describeCombatAction = (action: CombatAction) => {
  const parts: string[] = [];

  if (action.kind === "weapon_attack" || action.kind === "spell_attack") {
    const toHit = withSign(action.kind === "spell_attack" ? action.spellAttackBonus ?? action.toHitBonus : action.toHitBonus);
    if (toHit) {
      parts.push(`${toHit} to hit`);
    }
    if (action.weaponCanonicalKey) {
      parts.push("catalog weapon");
    }
    if (action.spellCanonicalKey) {
      parts.push("catalog spell");
    }
    if (action.damageDice) {
      const bonus = withSign(action.damageBonus);
      parts.push(`${action.damageDice}${bonus ?? ""}${action.damageType ? ` ${action.damageType}` : ""}`.trim());
    }
  } else if (action.kind === "saving_throw") {
    if (action.spellCanonicalKey) {
      parts.push("catalog spell");
    }
    if (action.saveAbility && typeof action.saveDc === "number") {
      parts.push(`${action.saveAbility} save DC ${action.saveDc}`);
    }
    if (action.damageDice) {
      const bonus = withSign(action.damageBonus);
      parts.push(`${action.damageDice}${bonus ?? ""}${action.damageType ? ` ${action.damageType}` : ""}`.trim());
    }
  } else if (action.kind === "heal") {
    if (action.spellCanonicalKey) {
      parts.push("catalog spell");
    }
    if (action.healDice) {
      const bonus = withSign(action.healBonus);
      parts.push(`heal ${action.healDice}${bonus ?? ""}`.trim());
    }
  } else if (action.kind === "utility") {
    parts.push("manual only");
  }

  if (typeof action.rangeMeters === "number") {
    parts.push(`${action.rangeMeters}m`);
  }

  if (typeof action.isMelee === "boolean") {
    parts.push(action.isMelee ? "melee" : "ranged");
  }

  return parts.join(" • ");
};
