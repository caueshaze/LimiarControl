const ITEM_PROPERTY_CONFIG = {
  ammunition: {
    labels: { en: "Ammunition", pt: "Municao" },
    aliases: ["ammunition", "ammo", "municao"],
  },
  finesse: {
    labels: { en: "Finesse", pt: "Acuidade" },
    aliases: ["finesse", "acuidade"],
  },
  heavy: {
    labels: { en: "Heavy", pt: "Pesada" },
    aliases: ["heavy", "pesada", "pesado"],
  },
  light: {
    labels: { en: "Light", pt: "Leve" },
    aliases: ["light", "leve"],
  },
  loading: {
    labels: { en: "Loading", pt: "Carregamento" },
    aliases: ["loading", "carregamento", "recarga"],
  },
  range: {
    labels: { en: "Range", pt: "Alcance" },
    aliases: ["range", "alcance", "ranged", "distancia", "a distancia"],
  },
  reach: {
    labels: { en: "Reach", pt: "Alcance estendido" },
    aliases: ["reach", "alcance estendido"],
  },
  special: {
    labels: { en: "Special", pt: "Especial" },
    aliases: ["special", "especial"],
  },
  thrown: {
    labels: { en: "Thrown", pt: "Arremesso" },
    aliases: ["thrown", "arremesso", "arremessavel"],
  },
  two_handed: {
    labels: { en: "Two-Handed", pt: "Duas maos" },
    aliases: ["two_handed", "two handed", "two-handed", "duas maos"],
  },
  versatile: {
    labels: { en: "Versatile", pt: "Versatil" },
    aliases: ["versatile", "versatil"],
  },
  stealth_disadvantage: {
    labels: { en: "Stealth disadvantage", pt: "Desvantagem em furtividade" },
    aliases: [
      "stealth_disadvantage",
      "stealth disadvantage",
      "disadvantage on stealth",
      "desvantagem em furtividade",
    ],
  },
} as const;

export type ItemPropertySlug = keyof typeof ITEM_PROPERTY_CONFIG;

export const ITEM_PROPERTY_SLUGS = Object.keys(
  ITEM_PROPERTY_CONFIG,
) as ItemPropertySlug[];

const normalizePropertyToken = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");

const ITEM_PROPERTY_ALIAS_TO_SLUG = Object.entries(ITEM_PROPERTY_CONFIG).reduce(
  (accumulator, [slug, config]) => {
    config.aliases.forEach((alias) => {
      accumulator[normalizePropertyToken(alias)] = slug as ItemPropertySlug;
    });
    accumulator[normalizePropertyToken(slug)] = slug as ItemPropertySlug;
    return accumulator;
  },
  {} as Record<string, ItemPropertySlug>,
);

type NormalizedPropertiesResult =
  | { ok: true; value: ItemPropertySlug[]; invalid: [] }
  | { ok: false; value: ItemPropertySlug[]; invalid: string[] };

export const resolveItemPropertySlug = (value: string): ItemPropertySlug | null => {
  if (!value.trim()) {
    return null;
  }
  return ITEM_PROPERTY_ALIAS_TO_SLUG[normalizePropertyToken(value)] ?? null;
};

export const normalizeItemProperties = (
  values: readonly string[] | null | undefined,
): NormalizedPropertiesResult => {
  const normalized: ItemPropertySlug[] = [];
  const invalid: string[] = [];
  const seen = new Set<ItemPropertySlug>();

  for (const entry of values ?? []) {
    const rawValue = String(entry ?? "").trim();
    if (!rawValue) {
      continue;
    }

    const slug = resolveItemPropertySlug(rawValue);
    if (!slug) {
      if (!invalid.includes(rawValue)) {
        invalid.push(rawValue);
      }
      continue;
    }

    if (!seen.has(slug)) {
      seen.add(slug);
      normalized.push(slug);
    }
  }

  if (invalid.length > 0) {
    return { ok: false, value: normalized, invalid };
  }

  return { ok: true, value: normalized, invalid: [] };
};

export const parseItemPropertiesInput = (
  input: string,
): NormalizedPropertiesResult => {
  if (!input.trim()) {
    return { ok: true, value: [], invalid: [] };
  }
  return normalizeItemProperties(input.split(","));
};

export const getItemPropertyLabel = (value: string, locale: string): string => {
  const slug = resolveItemPropertySlug(value);
  if (!slug) {
    return value.trim();
  }

  return locale === "pt"
    ? ITEM_PROPERTY_CONFIG[slug].labels.pt
    : ITEM_PROPERTY_CONFIG[slug].labels.en;
};

export const getItemPropertyLabels = (
  values: readonly string[] | null | undefined,
  locale: string,
) =>
  (values ?? [])
    .map((value) => getItemPropertyLabel(value, locale))
    .filter(Boolean);
