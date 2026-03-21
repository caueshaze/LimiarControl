import type { SessionEntityPlayer } from "../../../entities/session-entity";
import type { EntityCategory } from "../../../entities/campaign-entity";
import { CategoryBadge } from "../../campaign-entities";

type Props = {
  entity: SessionEntityPlayer;
};

export const PlayerEntityCard = ({ entity }: Props) => {
  const ce = entity.entity;
  if (!ce) return null;

  const displayName = entity.label ? `${ce.name} (${entity.label})` : ce.name;
  const category = (ce.category ?? "npc") as EntityCategory;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
      <div className="flex items-center gap-2">
        <p className="text-base font-semibold text-white">{displayName}</p>
        <CategoryBadge category={category} />
      </div>

      {/* HP / AC */}
      {(entity.currentHp != null || ce.baseAc != null) && (
        <div className="mt-1 flex gap-3 text-xs">
          {entity.currentHp != null && (
            <span className="rounded-lg bg-red-500/10 border border-red-500/20 px-2 py-0.5 font-bold text-red-400">
              HP {ce.baseHp != null ? `${entity.currentHp}/${ce.baseHp}` : entity.currentHp}
            </span>
          )}
          {ce.baseAc != null && (
            <span className="rounded-lg bg-sky-500/10 border border-sky-500/20 px-2 py-0.5 font-bold text-sky-400">
              AC {ce.baseAc}
            </span>
          )}
        </div>
      )}

      {ce.description && (
        <p className="mt-2 text-xs text-slate-400">{ce.description}</p>
      )}

      {/* Stats */}
      {ce.stats && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {(["str", "dex", "con", "int", "wis", "cha"] as const).map((key) => {
            const val = (ce.stats as Record<string, number | null | undefined>)?.[key];
            if (val == null) return null;
            return (
              <span key={key} className="rounded-lg bg-slate-800 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-300">
                {key} {val}
              </span>
            );
          })}
        </div>
      )}

      {ce.actions && (
        <div className="mt-2 text-xs text-slate-300">
          <span className="text-slate-500">Actions: </span>
          <span className="whitespace-pre-wrap">{ce.actions}</span>
        </div>
      )}

      {ce.notesPublic && (
        <p className="mt-2 text-xs text-slate-400">{ce.notesPublic}</p>
      )}

      {ce.imageUrl && (
        <img
          src={ce.imageUrl}
          alt={ce.name}
          className="mt-2 h-20 w-20 rounded-xl border border-slate-700 object-cover"
        />
      )}
    </div>
  );
};
