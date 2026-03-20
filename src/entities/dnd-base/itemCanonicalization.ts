export type DndItemNormalization = {
  persistedName: string;
  aliases: string[];
  lookupNames: string[];
};

export const DND_ITEM_NORMALIZATIONS: DndItemNormalization[] = [
  {
    persistedName: "Shield",
    aliases: ["Shield", "Escudo", "Wooden Shield"],
    lookupNames: ["Escudo", "Shield"],
  },
  {
    persistedName: "Shortsword",
    aliases: ["Shortsword", "Espada Curta"],
    lookupNames: ["Espada Curta", "Shortsword"],
  },
  {
    persistedName: "Mace",
    aliases: ["Mace", "Maça"],
    lookupNames: ["Maça", "Mace"],
  },
  {
    persistedName: "Warhammer",
    aliases: ["Warhammer", "Martelo de Guerra"],
    lookupNames: ["Martelo de Guerra", "Warhammer"],
  },
  {
    persistedName: "Longsword",
    aliases: ["Longsword", "Espada Longa"],
    lookupNames: ["Espada Longa", "Longsword"],
  },
  {
    persistedName: "Scimitar",
    aliases: ["Scimitar", "Cimitarra"],
    lookupNames: ["Cimitarra", "Scimitar"],
  },
  {
    persistedName: "Handaxe",
    aliases: ["Handaxe", "Machado de Mão"],
    lookupNames: ["Machado de Mão", "Handaxe"],
  },
  {
    persistedName: "Light Crossbow",
    aliases: ["Light Crossbow", "Besta Leve", "Crossbow, light"],
    lookupNames: ["Besta Leve", "Crossbow, light"],
  },
  {
    persistedName: "Crossbow bolt",
    aliases: ["Crossbow bolt", "Crossbow bolts", "Bolt"],
    lookupNames: ["Crossbow bolt"],
  },
  {
    persistedName: "Arcane Focus",
    aliases: ["Arcane Focus"],
    lookupNames: [],
  },
  {
    persistedName: "Druidic Focus",
    aliases: ["Druidic Focus"],
    lookupNames: [],
  },
  {
    persistedName: "Holy Symbol",
    aliases: ["Holy Symbol", "Holy symbol", "Holy Symbols", "Amulet", "Emblem", "Reliquary"],
    lookupNames: ["Amulet", "Emblem", "Reliquary"],
  },
  {
    persistedName: "Thieves' Tools",
    aliases: ["Thieves' Tools", "Thieves' tools"],
    lookupNames: ["Thieves' Tools"],
  },
  {
    persistedName: "Quiver",
    aliases: ["Quiver"],
    lookupNames: ["Quiver"],
  },
  {
    persistedName: "Forgery Kit",
    aliases: ["Forgery Kit", "Forgery kit"],
    lookupNames: ["Forgery Kit"],
  },
];

export const normalizeDndItemKey = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

const DND_ITEM_NORMALIZATION_BY_KEY = Object.fromEntries(
  DND_ITEM_NORMALIZATIONS.flatMap((entry) =>
    [...entry.aliases, entry.persistedName].map((alias) => [
      normalizeDndItemKey(alias),
      entry,
    ] as const),
  ),
);

export const getDndItemCanonicalization = (name: string) => {
  const normalizedName = normalizeDndItemKey(name);
  return normalizedName ? DND_ITEM_NORMALIZATION_BY_KEY[normalizedName] ?? null : null;
};

export const canonicalizeDndItemName = (name: string) => {
  const raw = name.trim();
  if (!raw) {
    return raw;
  }
  return getDndItemCanonicalization(raw)?.persistedName ?? raw;
};

export const getDndItemCanonicalKey = (name: string) =>
  normalizeDndItemKey(canonicalizeDndItemName(name));

export const getDndItemLookupNames = (name: string) =>
  getDndItemCanonicalization(name)?.lookupNames ?? [];

export const getDndItemAliases = (name: string) => {
  const raw = name.trim();
  if (!raw) {
    return [];
  }

  const entry = getDndItemCanonicalization(raw);
  if (!entry) {
    return [raw];
  }

  const seen = new Set<string>();
  return [entry.persistedName, ...entry.aliases, ...entry.lookupNames].filter((candidate) => {
    const key = normalizeDndItemKey(candidate);
    if (!key || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
};
