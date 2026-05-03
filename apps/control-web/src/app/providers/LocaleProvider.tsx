import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Locale, LocaleKey } from "../../shared/i18n";
import { dictionaries } from "../../shared/i18n";
import { LocaleContext } from "./localeContext";

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

  const value = useMemo(
    () => ({
      locale,
      setLocale: changeLocale,
      toggleLocale: () => changeLocale(locale === "en" ? "pt" : "en"),
      t: (key: LocaleKey) => dictionaries[locale][key] ?? dictionaries.en[key],
    }),
    [locale]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
};
