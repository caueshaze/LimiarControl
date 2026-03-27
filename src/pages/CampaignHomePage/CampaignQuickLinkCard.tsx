import { Link } from "react-router-dom";
import { useLocale } from "../../shared/hooks/useLocale";

type CampaignQuickLinkCardProps = {
  to: string;
  title: string;
  description: string;
  accent: "sky" | "emerald";
};

export const CampaignQuickLinkCard = ({
  to,
  title,
  description,
  accent,
}: CampaignQuickLinkCardProps) => {
  const { t } = useLocale();
  const accentStyles =
    accent === "sky"
      ? {
          border: "border-sky-400/18 hover:border-sky-300/30",
          glow: "bg-sky-400/16",
          badge: "border-sky-300/15 bg-sky-400/10 text-sky-100",
          text: "text-sky-200",
        }
      : {
          border: "border-emerald-400/18 hover:border-emerald-300/30",
          glow: "bg-emerald-400/16",
          badge: "border-emerald-300/15 bg-emerald-400/10 text-emerald-100",
          text: "text-emerald-200",
        };

  return (
    <Link
      to={to}
      className={`group relative overflow-hidden rounded-[28px] border ${accentStyles.border} bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_18px_50px_rgba(2,6,23,0.22)] transition hover:-translate-y-px`}
    >
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px)] bg-size-[42px_42px]" />
      <div className={`pointer-events-none absolute -right-8 top-0 h-32 w-32 rounded-full blur-[90px] ${accentStyles.glow}`} />

      <div className="relative flex h-full flex-col justify-between gap-8">
        <div>
          <span className={`inline-flex rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] ${accentStyles.badge}`}>
            {title}
          </span>
          <p className="mt-4 text-sm leading-7 text-slate-300">{description}</p>
        </div>

        <div className="flex items-center justify-between gap-4">
          <p className={`text-xs font-semibold uppercase tracking-[0.26em] transition ${accentStyles.text}`}>
            {title}
          </p>
          <span className="rounded-full border border-white/10 bg-white/4 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-200 transition group-hover:border-white/20 group-hover:bg-white/8">
            {t("campaignHome.openModule")} →
          </span>
        </div>
      </div>
    </Link>
  );
};
