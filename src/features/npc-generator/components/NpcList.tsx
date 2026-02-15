import type { NPC } from "../../../entities/npc";
import { useLocale } from "../../../shared/hooks/useLocale";
import { NpcCard } from "./NpcCard";

type NpcListProps = {
  npcs: NPC[];
  query: string;
  onQueryChange: (value: string) => void;
};

export const NpcList = ({ npcs, query, onQueryChange }: NpcListProps) => {
  const { t } = useLocale();

  return (
    <div className="space-y-4">
      <input
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
        placeholder={t("npc.search")}
      />
      {npcs.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
          {t("npc.empty")}
        </div>
      ) : (
        <div className="grid gap-4">
          {npcs.map((npc) => (
            <NpcCard key={npc.id} npc={npc} />
          ))}
        </div>
      )}
    </div>
  );
};
