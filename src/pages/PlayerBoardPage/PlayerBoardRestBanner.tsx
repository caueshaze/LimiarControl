import { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  restState: "exploration" | "short_rest" | "long_rest";
};

export const PlayerBoardRestBanner = ({ restState }: Props) => {
  const { t } = useLocale();

  if (restState === "exploration") {
    return null;
  }

  const isLongRest = restState === "long_rest";

  return (
    <section
      className={`rounded-[28px] border px-5 py-4 shadow-[0_16px_48px_rgba(2,6,23,0.16)] ${
        isLongRest
          ? "border-sky-400/20 bg-sky-500/10"
          : "border-amber-400/20 bg-amber-500/10"
      }`}
    >
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p
            className={`text-[11px] font-semibold uppercase tracking-[0.28em] ${
              isLongRest ? "text-sky-200" : "text-amber-200"
            }`}
          >
            {t("playerBoard.restStateTitle")}
          </p>
          <h2 className="mt-1 text-xl font-semibold text-white">
            {isLongRest
              ? t("playerBoard.restStateLong")
              : t("playerBoard.restStateShort")}
          </h2>
          <p className="mt-2 text-sm leading-7 text-slate-200">
            {isLongRest
              ? t("playerBoard.longRestDescription")
              : t("playerBoard.shortRestDescription")}
          </p>
        </div>
        <span
          className={`rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.22em] ${
            isLongRest
              ? "border-sky-300/30 text-sky-100"
              : "border-amber-300/30 text-amber-100"
          }`}
        >
          {isLongRest ? "GM Controlled" : "Hit Dice Open"}
        </span>
      </div>
    </section>
  );
};
