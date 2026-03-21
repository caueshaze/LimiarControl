import { useState } from "react";
import type { SessionEntity } from "../../../entities/session-entity";
import { CategoryBadge } from "../../campaign-entities";
import type { EntityCategory } from "../../../entities/campaign-entity";

type Props = {
  entity: SessionEntity;
  onToggleVisibility: (id: string) => Promise<void> | void;
  onUpdateHp: (id: string, hp: number | null) => Promise<void> | void;
  onRemove: (id: string) => Promise<void> | void;
};

export const SessionEntityRow = ({ entity, onToggleVisibility, onUpdateHp, onRemove }: Props) => {
  const [removing, setRemoving] = useState(false);

  const name = entity.entity?.name ?? "Unknown";
  const category = (entity.entity?.category ?? "npc") as EntityCategory;
  const displayName = entity.label ? `${name} (${entity.label})` : name;
  const hp = entity.currentHp;
  const maxHp = entity.entity?.baseHp ?? null;
  const adjustments = [-10, -5, -1, 1, 5, 10];

  const handleHpChange = (delta: number) => {
    const next = Math.max(0, (hp ?? 0) + delta);
    void onUpdateHp(entity.id, next);
  };

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await onRemove(entity.id);
    } finally {
      setRemoving(false);
    }
  };

  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2">
      {/* Visibility toggle */}
      <button
        type="button"
        onClick={() => void onToggleVisibility(entity.id)}
        className={`shrink-0 text-lg ${entity.visibleToPlayers ? "text-emerald-400" : "text-slate-600"}`}
        title={entity.visibleToPlayers ? "Visible to players — click to hide" : "Hidden — click to reveal"}
      >
        {entity.visibleToPlayers ? "👁" : "👁‍🗨"}
      </button>

      {/* Name + badge */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-white">{displayName}</span>
          <CategoryBadge category={category} />
        </div>
      </div>

      {/* HP control */}
      {hp != null && (
        <div className="flex items-center gap-1.5">
          {adjustments.map((delta) => (
            <button
              key={delta}
              type="button"
              onClick={() => handleHpChange(delta)}
              className={`rounded px-1.5 py-1 text-[10px] font-bold ${
                delta < 0
                  ? "bg-red-500/15 text-red-300 hover:bg-red-500/25"
                  : "bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25"
              }`}
            >
              {delta > 0 ? `+${delta}` : delta}
            </button>
          ))}
          <span className="min-w-14 text-center text-xs font-bold text-white">
            {maxHp != null ? `${hp}/${maxHp}` : hp}
          </span>
        </div>
      )}

      {/* Remove */}
      <button
        type="button"
        onClick={handleRemove}
        disabled={removing}
        className="shrink-0 rounded-full border border-red-500/30 px-2 py-1 text-[10px] text-red-400 hover:bg-red-500/10 disabled:opacity-50"
      >
        {removing ? "..." : "✕"}
      </button>
    </div>
  );
};
