import type { EntityCategory } from "../../../entities/campaign-entity";

const BADGE_STYLES: Record<EntityCategory, string> = {
  npc: "border-sky-500/30 bg-sky-500/10 text-sky-400",
  enemy: "border-red-500/30 bg-red-500/10 text-red-400",
  creature: "border-amber-500/30 bg-amber-500/10 text-amber-400",
  ally: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
};

const LABELS: Record<EntityCategory, string> = {
  npc: "NPC",
  enemy: "Enemy",
  creature: "Creature",
  ally: "Ally",
};

export const CategoryBadge = ({ category }: { category: EntityCategory }) => (
  <span
    className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${BADGE_STYLES[category] ?? BADGE_STYLES.npc}`}
  >
    {LABELS[category] ?? category}
  </span>
);
