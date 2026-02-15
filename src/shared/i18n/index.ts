import { enUS } from "./enUS";
import { ptBR } from "./ptBR";

export const dictionaries = {
  en: enUS,
  pt: ptBR,
} as const;

export type LocaleKey = keyof typeof enUS;
export type Locale = keyof typeof dictionaries;
