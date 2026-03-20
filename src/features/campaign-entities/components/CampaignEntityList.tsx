import type { CampaignEntity, CampaignEntityPayload, EntityCategory } from "../../../entities/campaign-entity";
import { useLocale } from "../../../shared/hooks/useLocale";
import { CampaignEntityCard } from "./CampaignEntityCard";

const CATEGORY_TABS: Array<EntityCategory | "all"> = ["all", "npc", "enemy", "creature", "ally"];

type Props = {
  entities: CampaignEntity[];
  query: string;
  onQueryChange: (query: string) => void;
  categoryFilter: EntityCategory | "all";
  onCategoryChange: (category: EntityCategory | "all") => void;
  onUpdate?: (entityId: string, payload: CampaignEntityPayload) => Promise<void> | void;
  onRemove?: (entityId: string) => Promise<void> | void;
};

export const CampaignEntityList = ({
  entities,
  query,
  onQueryChange,
  categoryFilter,
  onCategoryChange,
  onUpdate,
  onRemove,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="space-y-3">
      {/* Search + Category tabs */}
      <div className="space-y-2">
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={t("entity.search")}
          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none placeholder:text-slate-600"
        />
        <div className="flex rounded-full border border-slate-700 overflow-hidden text-[10px] font-semibold uppercase tracking-widest">
          {CATEGORY_TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => onCategoryChange(tab)}
              className={`flex-1 px-2 py-1.5 transition-colors ${
                categoryFilter === tab
                  ? "bg-slate-700 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {t(`entity.category.${tab}`)}
            </button>
          ))}
        </div>
      </div>

      {/* Entity list */}
      {entities.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-400">
          {t("entity.empty")}
        </div>
      ) : (
        <div className="space-y-2">
          {entities.map((entity) => (
            <CampaignEntityCard
              key={entity.id}
              entity={entity}
              onUpdate={onUpdate}
              onRemove={onRemove}
            />
          ))}
        </div>
      )}
    </div>
  );
};
