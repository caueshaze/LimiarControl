export type LocaleLike = "en" | "pt" | string;
export type LabelEntry = { en: string; pt: string };

export const label = <T extends string>(en: T, pt: string) => ({ en, pt });

export const displayLabel = (labels: LabelEntry, locale: LocaleLike) =>
  locale === "pt" ? labels.pt : labels.en;

export const humanizeFallback = (value: string) =>
  value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());

export const normalizeLookup = (value: string | null | undefined) =>
  String(value ?? "")
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[_-]+/g, " ");
