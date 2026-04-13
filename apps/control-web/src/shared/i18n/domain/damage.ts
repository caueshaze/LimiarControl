import type { BaseItemDamageType } from "../../../entities/base-item";
import type { SpellDamageType } from "../../../entities/base-spell";
import {
  displayLabel,
  humanizeFallback,
  label,
  normalizeLookup,
  type LabelEntry,
  type LocaleLike,
} from "./shared";

const DAMAGE_TYPE_LABELS: Record<string, LabelEntry> = {
  acid: label("Acid", "Ácido"),
  bludgeoning: label("Bludgeoning", "Contundente"),
  cold: label("Cold", "Frio"),
  fire: label("Fire", "Fogo"),
  force: label("Force", "Força"),
  lightning: label("Lightning", "Elétrico"),
  necrotic: label("Necrotic", "Necrótico"),
  piercing: label("Piercing", "Perfurante"),
  poison: label("Poison", "Veneno"),
  psychic: label("Psychic", "Psíquico"),
  radiant: label("Radiant", "Radiante"),
  slashing: label("Slashing", "Cortante"),
  thunder: label("Thunder", "Trovão"),
} as const;

export const localizeDamageType = (
  value: string | null | undefined,
  locale: LocaleLike,
) => {
  const normalized = normalizeLookup(value);
  if (!normalized) {
    return null;
  }
  return DAMAGE_TYPE_LABELS[normalized]
    ? displayLabel(DAMAGE_TYPE_LABELS[normalized], locale)
    : value?.trim() ?? null;
};

export const formatDamageLabel = (
  damageDice: string | null | undefined,
  damageType: string | null | undefined,
  locale: LocaleLike,
) => {
  const typeLabel = localizeDamageType(damageType, locale);
  if (damageDice?.trim()) {
    return `${damageDice}${typeLabel ? ` ${typeLabel}` : ""}`;
  }
  return typeLabel;
};

export const localizeDamageAdminFallback = (
  value: BaseItemDamageType | SpellDamageType | string,
  locale: LocaleLike,
) => {
  const damageLabel = localizeDamageType(value, locale);
  return damageLabel && damageLabel !== value ? damageLabel : humanizeFallback(value);
};
