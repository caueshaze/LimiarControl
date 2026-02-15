import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Locale, LocaleKey } from "../../shared/i18n";
import { dictionaries } from "../../shared/i18n";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  t: (key: LocaleKey) => string;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

const DEFAULT_LOCALE: Locale = "en";

const readLocale = (): Locale => {
  if (typeof navigator === "undefined") {
    return DEFAULT_LOCALE;
  }
  return navigator.language.toLowerCase().startsWith("pt") ? "pt" : "en";
};

export const LocaleProvider = ({ children }: { children: ReactNode }) => {
  const [locale, setLocale] = useState<Locale>(readLocale);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      setLocale,
      toggleLocale: () => setLocale((current) => (current === "en" ? "pt" : "en")),
      t: (key) => dictionaries[locale][key] ?? dictionaries.en[key],
    }),
    [locale]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
};

export const useLocaleContext = () => {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error("useLocale must be used within LocaleProvider");
  }
  return context;
};
