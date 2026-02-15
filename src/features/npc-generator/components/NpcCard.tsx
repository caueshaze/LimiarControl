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
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
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
          className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200"
        >
          {expanded ? t("npc.hide") : t("npc.details")}
        </button>
      </div>
      {expanded && (
        <div className="mt-3 space-y-2 text-xs text-slate-300">
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
