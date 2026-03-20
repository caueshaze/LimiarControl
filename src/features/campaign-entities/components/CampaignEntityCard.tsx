import { useState } from "react";
import type { CampaignEntity, CampaignEntityPayload } from "../../../entities/campaign-entity";
import { useLocale } from "../../../shared/hooks/useLocale";
import { CategoryBadge } from "./CategoryBadge";
import { CampaignEntityForm } from "./CampaignEntityForm";

type Props = {
  entity: CampaignEntity;
  onUpdate?: (entityId: string, payload: CampaignEntityPayload) => Promise<void> | void;
  onRemove?: (entityId: string) => Promise<void> | void;
};

export const CampaignEntityCard = ({ entity, onUpdate, onRemove }: Props) => {
  const { t } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [removing, setRemoving] = useState(false);

  const handleRemove = async () => {
    if (!onRemove) return;
    setRemoving(true);
    try {
      await onRemove(entity.id);
    } finally {
      setRemoving(false);
    }
  };

  if (editing && onUpdate) {
    return (
      <CampaignEntityForm
        initial={entity}
        onSave={async (payload) => {
          await onUpdate(entity.id, payload);
          setEditing(false);
        }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="truncate text-base font-semibold text-slate-100">{entity.name}</p>
            <CategoryBadge category={entity.category} />
          </div>
          {/* HP / AC inline */}
          {(entity.baseHp != null || entity.baseAc != null) && (
            <div className="mt-1 flex gap-3 text-xs text-slate-400">
              {entity.baseHp != null && <span>HP {entity.baseHp}</span>}
              {entity.baseAc != null && <span>AC {entity.baseAc}</span>}
            </div>
          )}
          {entity.description && (
            <p className="mt-1 text-xs text-slate-400 line-clamp-2">{entity.description}</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="shrink-0 rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-200"
        >
          {expanded ? t("entity.card.hide") : t("entity.card.details")}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 space-y-2 text-xs text-slate-300">
          {/* Stats */}
          {entity.stats && (
            <div className="flex flex-wrap gap-2">
              {(["str", "dex", "con", "int", "wis", "cha"] as const).map((key) => {
                const val = (entity.stats as Record<string, number | null | undefined>)?.[key];
                if (val == null) return null;
                return (
                  <span key={key} className="rounded-lg bg-slate-800 px-2 py-1 text-[10px] font-bold uppercase text-slate-300">
                    {key} {val}
                  </span>
                );
              })}
            </div>
          )}

          {entity.actions && (
            <div>
              <span className="text-slate-500">{t("entity.form.actions")}: </span>
              <span className="whitespace-pre-wrap">{entity.actions}</span>
            </div>
          )}

          {entity.notesPublic && (
            <div>
              <span className="text-slate-500">{t("entity.form.notesPublic")}: </span>
              {entity.notesPublic}
            </div>
          )}

          {entity.notesPrivate && (
            <div>
              <span className="text-amber-500/70">{t("entity.form.notesPrivate")}: </span>
              {entity.notesPrivate}
            </div>
          )}

          {entity.imageUrl && (
            <img
              src={entity.imageUrl}
              alt={entity.name}
              className="mt-2 h-24 w-24 rounded-xl border border-slate-700 object-cover"
            />
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-2">
            {onUpdate && (
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
              >
                {t("entity.card.edit")}
              </button>
            )}
            {onRemove && (
              <button
                type="button"
                onClick={handleRemove}
                disabled={removing}
                className="rounded-full border border-red-500/30 px-3 py-1 text-xs text-red-400 hover:bg-red-500/10 disabled:opacity-50"
              >
                {removing ? "..." : t("entity.card.remove")}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
