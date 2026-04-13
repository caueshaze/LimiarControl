import { useLocale } from "../../shared/hooks/useLocale";

export const EmptyPartyState = () => {
  const { t } = useLocale();

  return (
    <div className="relative overflow-hidden rounded-4xl border border-dashed border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.78),rgba(2,6,23,0.92))] px-8 py-14 text-center">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(139,92,246,0.16),transparent_32%)]" />
      <div className="relative mx-auto max-w-xl space-y-5">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[22px] border border-limiar-300/15 bg-limiar-400/10 font-display text-2xl text-limiar-100">
          ✦
        </div>
        <div>
          <h3 className="text-2xl font-semibold text-white">{t("gm.home.emptyPartyTitle")}</h3>
          <p className="mt-3 text-sm leading-7 text-slate-300">{t("gm.home.emptyPartyDescription")}</p>
        </div>
        <p className="mx-auto max-w-md text-xs uppercase tracking-[0.22em] text-slate-500">
          {t("gm.home.emptyPartyHint")}
        </p>
      </div>
    </div>
  );
};
