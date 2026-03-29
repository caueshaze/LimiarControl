import { useState } from "react";
import type { SessionEntity } from "../../../entities/session-entity";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  entity: SessionEntity;
  onToggleVisibility: (id: string) => Promise<void> | void;
  onRemove: (id: string) => Promise<void> | void;
};

export const SessionEntityRow = ({ entity, onToggleVisibility, onRemove }: Props) => {
  const { t } = useLocale();
  const [removing, setRemoving] = useState(false);

  const name = entity.entity?.name ?? "Unknown";
  const displayName = entity.label ? `${name} (${entity.label})` : name;
  const description = entity.entity?.description ?? null;
  const imageUrl = entity.entity?.imageUrl ?? null;

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await onRemove(entity.id);
    } finally {
      setRemoving(false);
    }
  };

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
      {/* Image */}
      <div className="shrink-0">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={displayName}
            className="h-12 w-12 rounded-xl object-cover"
          />
        ) : (
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-800/60 text-lg text-slate-500">
            ?
          </div>
        )}
      </div>

      {/* Name + description */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-white">{displayName}</p>
        {description && (
          <p className="mt-0.5 line-clamp-2 text-xs text-slate-400">{description}</p>
        )}
      </div>

      {/* Controls */}
      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={() => void onToggleVisibility(entity.id)}
          className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.18em] transition ${
            entity.visibleToPlayers
              ? "border-emerald-500/30 bg-emerald-500/12 text-emerald-200 hover:bg-emerald-500/18"
              : "border-slate-700 bg-slate-800/70 text-slate-300 hover:bg-slate-800"
          }`}
          title={entity.visibleToPlayers ? t("entity.session.hide") : t("entity.session.reveal")}
        >
          {entity.visibleToPlayers ? t("entity.session.hide") : t("entity.session.reveal")}
        </button>
        <button
          type="button"
          onClick={handleRemove}
          disabled={removing}
          className="rounded-full border border-red-500/30 px-2 py-1 text-[10px] text-red-400 hover:bg-red-500/10 disabled:opacity-50"
        >
          {removing ? "..." : "✕"}
        </button>
      </div>
    </div>
  );
};
