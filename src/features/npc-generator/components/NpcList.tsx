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
        className="w-full rounded-[20px] border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-limiar-300/35"
        placeholder={t("npc.search")}
      />
      {npcs.length === 0 ? (
        <div className="rounded-[24px] border border-dashed border-white/10 bg-white/[0.03] p-5 text-sm leading-7 text-slate-300">
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
