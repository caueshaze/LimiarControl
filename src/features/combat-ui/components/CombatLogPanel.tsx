import { useLocale } from "../../../shared/hooks/useLocale";
import { CombatLogEntries } from "./CombatLogEntries";
import type { CombatLogEntry } from "../types";

type Props = {
  logs: CombatLogEntry[];
};

export const CombatLogPanel = ({ logs }: Props) => {
  const { t } = useLocale();

  return (
    <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.94))] p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("combatUi.logEyebrow")}
          </p>
          <h3 className="mt-2 text-lg font-semibold text-white">{t("combatUi.combatLog")}</h3>
        </div>
      </div>

      <div className="mt-4">
        <CombatLogEntries emptyLabel={t("combatUi.logEmpty")} logs={logs} />
      </div>
    </section>
  );
};
