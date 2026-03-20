import { useState } from "react";
import type { NPC } from "../../../entities/npc";
import { useLocale } from "../../../shared/hooks/useLocale";

type NpcCardProps = {
  npc: NPC;
};

export const NpcCard = ({ npc }: NpcCardProps) => {
  const { t } = useLocale();
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-[24px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-5 text-sm text-slate-200 shadow-[0_18px_50px_rgba(2,6,23,0.18)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-base font-semibold text-slate-100">{npc.name}</p>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
            {[npc.race, npc.role].filter(Boolean).join(" · ")}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-white/20 hover:bg-white/[0.08]"
        >
          {expanded ? t("npc.hide") : t("npc.details")}
        </button>
      </div>
      {expanded && (
        <div className="mt-4 space-y-2 rounded-[18px] border border-white/8 bg-white/[0.03] p-4 text-xs text-slate-300">
          <p>
            <span className="text-slate-400">{t("npc.trait")}</span> {npc.trait}
          </p>
          <p>
            <span className="text-slate-400">{t("npc.goal")}</span> {npc.goal}
          </p>
          {npc.secret && (
            <p>
              <span className="text-slate-400">{t("npc.secret")}</span> {npc.secret}
            </p>
          )}
          {npc.notes && (
            <p>
              <span className="text-slate-400">{t("npc.notes")}</span> {npc.notes}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
