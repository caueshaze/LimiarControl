export type SpellAuthorityCandidate = {
  campaignSpellId?: string | null;
  canonicalKey?: string | null;
  name?: string | null;
};

const normalizeSpellAuthorityValue = (value?: string | null) => {
  const normalized = value?.trim().toLowerCase();
  return normalized ? normalized : null;
};

export const normalizeSpellAuthorityName = (name?: string | null) => {
  const normalized = normalizeSpellAuthorityValue(name);
  return normalized ? normalized.replace(/\s+/g, " ") : null;
};

export type SpellAuthorityReference =
  | {
      kind: "campaign";
      key: string;
      value: string;
    }
  | {
      kind: "canonical";
      key: string;
      value: string;
    }
  | {
      kind: "name";
      key: string;
      value: string;
    };

/**
 * Returns the authoritative spell identity using explicit precedence:
 * campaignSpellId > canonicalKey > name.
 */
export const getSpellAuthorityReference = (
  spell: SpellAuthorityCandidate
): SpellAuthorityReference | null => {
  const campaignSpellId = normalizeSpellAuthorityValue(spell.campaignSpellId);
  if (campaignSpellId) {
    return {
      kind: "campaign",
      key: `campaign:${campaignSpellId}`,
      value: campaignSpellId
    };
  }

  const canonicalKey = normalizeSpellAuthorityValue(spell.canonicalKey);
  if (canonicalKey) {
    return {
      kind: "canonical",
      key: `canonical:${canonicalKey}`,
      value: canonicalKey
    };
  }

  const name = normalizeSpellAuthorityName(spell.name);
  if (name) {
    return {
      kind: "name",
      key: `name:${name}`,
      value: name
    };
  }

  return null;
};

export const getSpellAuthorityKey = (spell: SpellAuthorityCandidate) =>
  getSpellAuthorityReference(spell)?.key ?? null;

export const isSameSpellAuthority = (
  left: SpellAuthorityCandidate,
  right: SpellAuthorityCandidate
) => {
  const leftKey = getSpellAuthorityKey(left);
  return leftKey !== null && leftKey === getSpellAuthorityKey(right);
};

/**
 * Resolves a spell entry from a catalog/collection using the explicit
 * authority precedence. If a stronger identifier exists and fails to match,
 * this function does not silently fall back to weaker identifiers.
 */
export const resolveSpellByAuthority = <T extends SpellAuthorityCandidate>(
  spells: readonly T[],
  spell: SpellAuthorityCandidate
): T | undefined => {
  const authority = getSpellAuthorityReference(spell);
  if (!authority) {
    return undefined;
  }

  return spells.find((entry) => {
    const entryAuthority = getSpellAuthorityReference(entry);
    return entryAuthority?.key === authority.key;
  });
};
