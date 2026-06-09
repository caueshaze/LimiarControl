export type CreationPersonalityFields = {
  personalityTraits: string;
  ideals: string;
  bonds: string;
  flaws: string;
};

const PERSONALITY_LABELS = {
  personalityTraits: ["Traços de personalidade", "Personality Traits"],
  ideals: ["Ideais", "Ideals"],
  bonds: ["Ligações", "Bonds"],
  flaws: ["Defeitos", "Flaws"],
} as const;

const PERSONALITY_KEYS = [
  "personalityTraits",
  "ideals",
  "bonds",
  "flaws",
] as const satisfies readonly (keyof CreationPersonalityFields)[];

export const EMPTY_CREATION_PERSONALITY_FIELDS: CreationPersonalityFields = {
  personalityTraits: "",
  ideals: "",
  bonds: "",
  flaws: "",
};

const escapeRegex = (value: string) =>
  value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

export const parseCreationPersonalityFields = (
  value: string,
): CreationPersonalityFields => {
  const trimmed = value.trim();
  if (!trimmed) {
    return EMPTY_CREATION_PERSONALITY_FIELDS;
  }

  const labels = PERSONALITY_KEYS.flatMap((key) => PERSONALITY_LABELS[key]);
  const labelPattern = labels.map(escapeRegex).join("|");
  const matcher = new RegExp(
    `^(?<label>${labelPattern}):\\s*(?<body>[\\s\\S]*?)(?=^(?:${labelPattern}):\\s*|$)`,
    "gmu",
  );

  const result: CreationPersonalityFields = { ...EMPTY_CREATION_PERSONALITY_FIELDS };
  let matchedAny = false;

  for (const match of trimmed.matchAll(matcher)) {
    const label = match.groups?.label?.trim();
    const body = match.groups?.body?.trim() ?? "";
    const key = PERSONALITY_KEYS.find((entry) => PERSONALITY_LABELS[entry].includes(label as never));
    if (!key) {
      continue;
    }
    result[key] = body;
    matchedAny = true;
  }

  if (!matchedAny) {
    return {
      ...EMPTY_CREATION_PERSONALITY_FIELDS,
      personalityTraits: trimmed,
    };
  }

  return result;
};

export const composeCreationPersonalityFields = (
  fields: CreationPersonalityFields,
): string => {
  const sections = [
    ["Traços de personalidade", fields.personalityTraits.trim()],
    ["Ideais", fields.ideals.trim()],
    ["Ligações", fields.bonds.trim()],
    ["Defeitos", fields.flaws.trim()],
  ].filter(([, body]) => body.length > 0);

  if (sections.length === 0) {
    return "";
  }

  return sections.map(([label, body]) => `${label}: ${body}`).join("\n\n");
};
