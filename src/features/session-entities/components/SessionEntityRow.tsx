import { useState } from "react";
import type { SessionEntity } from "../../../entities/session-entity";
import { CategoryBadge } from "../../campaign-entities";
import type { EntityCategory } from "../../../entities/campaign-entity";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  entity: SessionEntity;
  onToggleVisibility: (id: string) => Promise<void> | void;
  onUpdateHp: (id: string, hp: number | null) => Promise<void> | void;
  onRemove: (id: string) => Promise<void> | void;
};

export const SessionEntityRow = ({ entity, onToggleVisibility, onUpdateHp, onRemove }: Props) => {
  const { t } = useLocale();
  const [removing, setRemoving] = useState(false);

  const name = entity.entity?.name ?? "Unknown";
  const category = (entity.entity?.category ?? "npc") as EntityCategory;
  const displayName = entity.label ? `${name} (${entity.label})` : name;
  const hp = entity.currentHp;
  const maxHp = entity.entity?.baseHp ?? null;
  const adjustments = [-10, -5, -1, 1, 5, 10];
  const isDead = typeof hp === "number" && hp <= 0;

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
        className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.18em] transition ${
          entity.visibleToPlayers
            ? "border-emerald-500/30 bg-emerald-500/12 text-emerald-200 hover:bg-emerald-500/18"
            : "border-slate-700 bg-slate-800/70 text-slate-300 hover:bg-slate-800"
        }`}
        title={entity.visibleToPlayers ? t("entity.session.hide") : t("entity.session.reveal")}
      >
        {entity.visibleToPlayers ? t("entity.session.hide") : t("entity.session.reveal")}
      </button>

      {/* Name + badge */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-white">{displayName}</span>
          <CategoryBadge category={category} />
          {isDead && (
            <span className="rounded-full border border-red-500/30 bg-red-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.18em] text-red-200">
              {t("entity.dead")}
            </span>
          )}
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
