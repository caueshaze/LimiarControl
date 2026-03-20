import { useEffect, useMemo, useState } from "react";
import type { CampaignEntity } from "../../../entities/campaign-entity";
import { campaignEntitiesRepo } from "../../../shared/api/campaignEntitiesRepo";
import { CategoryBadge } from "../../campaign-entities";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  campaignId: string;
  onAdd: (campaignEntityId: string, label?: string | null, currentHp?: number | null) => Promise<void> | void;
  onClose: () => void;
};

export const AddEntityToSessionPanel = ({ campaignId, onAdd, onClose }: Props) => {
  const { t } = useLocale();
  const [entities, setEntities] = useState<CampaignEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [adding, setAdding] = useState<string | null>(null);

  useEffect(() => {
    campaignEntitiesRepo
      .list(campaignId)
      .then((data) => setEntities(Array.isArray(data) ? data : []))
      .catch(() => setEntities([]))
      .finally(() => setLoading(false));
  }, [campaignId]);

  const filtered = useMemo(() => {
    if (!search.trim()) return entities;
    const lower = search.trim().toLowerCase();
    return entities.filter((e) => e.name.toLowerCase().includes(lower));
  }, [entities, search]);

  const handleAdd = async (entity: CampaignEntity) => {
    setAdding(entity.id);
    try {
      await onAdd(entity.id, null, entity.baseHp);
    } finally {
      setAdding(null);
    }
  };

  return (
    <div className="space-y-3 rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-100">{t("entity.session.addTitle")}</p>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-slate-400 hover:text-slate-200"
        >
          ✕
        </button>
      </div>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder={t("entity.search")}
        className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none placeholder:text-slate-600"
        autoFocus
      />
      {loading ? (
        <p className="text-xs text-slate-500">{t("entity.loading")}</p>
      ) : filtered.length === 0 ? (
        <p className="text-xs text-slate-500">{t("entity.empty")}</p>
      ) : (
        <div className="max-h-60 space-y-1 overflow-y-auto">
          {filtered.map((entity) => (
            <button
              key={entity.id}
              type="button"
              disabled={adding === entity.id}
              onClick={() => void handleAdd(entity)}
              className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50"
            >
              <span className="flex-1 truncate font-medium">{entity.name}</span>
              <CategoryBadge category={entity.category} />
              {entity.baseHp != null && (
                <span className="text-[10px] text-slate-500">HP {entity.baseHp}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
