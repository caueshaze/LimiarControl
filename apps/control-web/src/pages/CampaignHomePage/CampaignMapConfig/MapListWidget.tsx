import type { CampaignMapConfig } from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";
import { ManagedImage } from "../../../shared/ui";
import { isMapReady } from "./utils";

type MapListWidgetProps = {
  maps: CampaignMapConfig[];
  selectedMapId: string | null;
  isCreatingNew: boolean;
  onEditMap: (map: CampaignMapConfig) => void;
  onPreviewMap: (map: CampaignMapConfig) => void;
};

export const MapListWidget = ({
  maps,
  selectedMapId,
  isCreatingNew,
  onEditMap,
  onPreviewMap,
}: MapListWidgetProps) => {
  const { t } = useLocale();

  if (maps.length === 0) {
    return null;
  }

  return (
    <>
      {maps.map((map) => {
        const ready = isMapReady(map);
        const selected = !isCreatingNew && selectedMapId === map.id;
        return (
          <div
            key={map.id}
            role="button"
            tabIndex={0}
            onClick={() => onPreviewMap(map)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onPreviewMap(map);
              }
            }}
            className={`cursor-pointer overflow-hidden rounded-3xl border text-left transition-all ${
              selected
                ? "border-limiar-400/60 bg-limiar-500/10 shadow-lg shadow-limiar-950/20"
                : "border-slate-800 bg-slate-950/60 hover:border-slate-700"
            }`}
          >
            <div className="relative h-36 overflow-hidden border-b border-white/6 bg-slate-950">
              {map.imageUrl ? (
                <ManagedImage
                  src={map.imageUrl}
                  alt={map.mapName ?? t("campaignHome.mapUntitled")}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center px-4 text-center text-xs text-slate-500">
                  {t("campaignHome.mapPreviewEmpty")}
                </div>
              )}
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onEditMap(map);
                }}
                aria-label={t("campaignHome.mapEdit")}
                className="absolute right-2 top-2 flex items-center gap-1 rounded-full border border-slate-700 bg-slate-950/85 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-limiar-100 hover:border-limiar-400/60 hover:bg-slate-900"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-3 w-3"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden
                >
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
                </svg>
                {t("campaignHome.mapEdit")}
              </button>
            </div>
            <div className="space-y-3 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">
                    {map.mapName || t("campaignHome.mapUntitled")}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    {map.gridWidth != null && map.gridHeight != null
                      ? `${map.gridWidth} x ${map.gridHeight}`
                      : t("campaignHome.mapStatusDraft")}
                  </p>
                </div>
                <span
                  className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
                    ready
                      ? "border border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
                      : "border border-amber-300/20 bg-amber-300/10 text-amber-100"
                  }`}
                >
                  {ready
                    ? t("campaignHome.mapStatusReady")
                    : t("campaignHome.mapStatusDraft")}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
};
