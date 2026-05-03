import { createContext } from "react";
import type { Locale, LocaleKey } from "../../shared/i18n";

export type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  t: (key: LocaleKey) => string;
};

export const LocaleContext = createContext<LocaleContextValue | null>(null);
