import { useLocale } from "../../shared/hooks/useLocale";

export type CatalogMode = "create" | "library";

type Props = {
  mode: CatalogMode;
  createTitle: string;
  libraryTitle: string;
  onChange: (mode: CatalogMode) => void;
};

export const CatalogModeSwitch = ({
  mode,
  createTitle,
  libraryTitle,
  onChange,
}: Props) => {
  const { t } = useLocale();

  return (
    <section className="rounded-[34px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.84),rgba(2,6,23,0.96))] p-3 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
      <div className="grid gap-2 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => onChange("create")}
          className={`rounded-3xl px-5 py-5 text-left transition ${
            mode === "create"
              ? "border border-violet-300/20 bg-violet-400/10 text-white shadow-[0_18px_40px_rgba(167,139,250,0.08)]"
              : "border border-transparent bg-white/3 text-slate-300 hover:bg-white/6"
          }`}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
            {t("catalog.switchCreate")}
          </p>
          <p className="mt-2 text-lg font-semibold text-inherit">{createTitle}</p>
          <p className="mt-2 text-sm leading-7 text-slate-300">
            {t("catalog.switchCreateDescription")}
          </p>
        </button>
        <button
          type="button"
          onClick={() => onChange("library")}
          className={`rounded-3xl px-5 py-5 text-left transition ${
            mode === "library"
              ? "border border-sky-300/20 bg-sky-400/10 text-white shadow-[0_18px_40px_rgba(56,189,248,0.08)]"
              : "border border-transparent bg-white/3 text-slate-300 hover:bg-white/6"
          }`}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
            {t("catalog.switchLibrary")}
          </p>
          <p className="mt-2 text-lg font-semibold text-inherit">{libraryTitle}</p>
          <p className="mt-2 text-sm leading-7 text-slate-300">
            {t("catalog.switchLibraryDescription")}
          </p>
        </button>
      </div>
    </section>
  );
};
