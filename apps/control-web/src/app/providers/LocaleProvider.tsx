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

const LOCALE_STORAGE_KEY = "app-locale";

const readLocale = (): Locale => {
  try {
    const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (stored === "en" || stored === "pt") return stored;
  } catch {}
  return "pt";
};

export const LocaleProvider = ({ children }: { children: ReactNode }) => {
  const [locale, setLocale] = useState<Locale>(readLocale);

  const changeLocale = (next: Locale) => {
    try { localStorage.setItem(LOCALE_STORAGE_KEY, next); } catch {}
    setLocale(next);
  };

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      setLocale: changeLocale,
      toggleLocale: () => changeLocale(locale === "en" ? "pt" : "en"),
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
