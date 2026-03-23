import {
  normalizeCampaignEntityOverrides,
  type AbilityName,
  type CampaignEntityPayload,
  type CombatAction,
  type SkillName,
} from "../../../../entities/campaign-entity";

const sanitizeNumericMap = <T extends string>(value: Partial<Record<T, number | null>>) =>
  Object.fromEntries(
    Object.entries(value).filter(([, entryValue]) => typeof entryValue === "number"),
  ) as Partial<Record<T, number>>;

const sanitizeCombatActionForSubmit = (action: CombatAction): CombatAction | null => {
  const name = action.name.trim();
  if (!name) {
    return null;
  }

  const damageDice = action.damageDice?.trim() || null;
  const healDice = action.healDice?.trim() || null;
  const description = action.description?.trim() || null;
  const campaignItemId = action.campaignItemId?.trim() || null;
  const weaponCanonicalKey = action.weaponCanonicalKey?.trim() || null;
  const spellCanonicalKey = action.spellCanonicalKey?.trim() || null;

  if (action.kind === "utility") {
    return {
      id: action.id,
      name,
      kind: action.kind,
      description,
    };
  }

  if (action.kind === "weapon_attack") {
    return {
      id: action.id,
      name,
      kind: action.kind,
      campaignItemId,
      weaponCanonicalKey,
      toHitBonus: action.toHitBonus ?? null,
      damageDice,
      damageBonus: action.damageBonus ?? null,
      damageType: action.damageType ?? null,
      rangeMeters: action.rangeMeters ?? null,
      isMelee: action.isMelee ?? null,
      description,
    };
  }

  if (action.kind === "spell_attack") {
    return {
      id: action.id,
      name,
      kind: action.kind,
      spellCanonicalKey,
      toHitBonus: action.toHitBonus ?? null,
      spellAttackBonus: action.spellAttackBonus ?? null,
      damageDice,
      damageBonus: action.damageBonus ?? null,
      damageType: action.damageType ?? null,
      rangeMeters: action.rangeMeters ?? null,
      castAtLevel: action.castAtLevel ?? null,
      description,
    };
  }

  if (action.kind === "saving_throw") {
    return {
      id: action.id,
      name,
      kind: action.kind,
      spellCanonicalKey,
      damageDice,
      damageBonus: action.damageBonus ?? null,
      damageType: action.damageType ?? null,
      rangeMeters: action.rangeMeters ?? null,
      saveAbility: action.saveAbility ?? null,
      saveDc: action.saveDc ?? null,
      castAtLevel: action.castAtLevel ?? null,
      description,
    };
  }

  return {
    id: action.id,
    name,
    kind: action.kind,
    spellCanonicalKey,
    healDice,
    healBonus: action.healBonus ?? null,
    castAtLevel: action.castAtLevel ?? null,
    description,
  };
};

const hasSpellcastingValue = (spellcasting: CampaignEntityPayload["spellcasting"]) =>
  Boolean(
    spellcasting &&
      (spellcasting.ability != null ||
        typeof spellcasting.saveDc === "number" ||
        typeof spellcasting.attackBonus === "number"),
  );

export const buildCampaignEntitySubmitPayload = (
  form: CampaignEntityPayload,
): CampaignEntityPayload => {
  const normalizedOverrides = normalizeCampaignEntityOverrides(form);

  return {
    ...form,
    name: form.name.trim(),
    creatureSubtype: form.creatureSubtype?.trim() || null,
    description: form.description?.trim() || null,
    imageUrl: form.imageUrl?.trim() || null,
    initiativeBonus: normalizedOverrides.initiativeBonus,
    abilities: { ...form.abilities },
    savingThrows: sanitizeNumericMap<AbilityName>(normalizedOverrides.savingThrows),
    skills: sanitizeNumericMap<SkillName>(normalizedOverrides.skills),
    senses:
      form.senses && Object.values(form.senses).some((value) => typeof value === "number")
        ? form.senses
        : null,
    spellcasting: hasSpellcastingValue(form.spellcasting) ? form.spellcasting : null,
    damageResistances: [...form.damageResistances],
    damageImmunities: [...form.damageImmunities],
    damageVulnerabilities: [...form.damageVulnerabilities],
    conditionImmunities: [...form.conditionImmunities],
    combatActions: form.combatActions
      .map(sanitizeCombatActionForSubmit)
      .filter((action): action is CombatAction => Boolean(action)),
    actions: form.actions?.trim() || null,
    notesPrivate: form.notesPrivate?.trim() || null,
    notesPublic: form.notesPublic?.trim() || null,
  };
};
