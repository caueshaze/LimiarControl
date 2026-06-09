import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  zoom: number;
  canZoomIn: boolean;
  canZoomOut: boolean;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
};

export const MapZoomControls = ({
  zoom,
  canZoomIn,
  canZoomOut,
  onZoomIn,
  onZoomOut,
  onReset,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900/70 px-1 py-1">
      <button
        type="button"
        onClick={onZoomOut}
        disabled={!canZoomOut}
        aria-label={t("campaignHome.mapPreviewZoomOut")}
        className="flex h-6 w-6 items-center justify-center rounded-full text-sm font-bold text-slate-200 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
      >
        −
      </button>
      <button
        type="button"
        onClick={onReset}
        aria-label={t("campaignHome.mapPreviewZoomReset")}
        className="min-w-12 rounded-full px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-200 hover:bg-white/10"
      >
        {`${Math.round(zoom * 100)}%`}
      </button>
      <button
        type="button"
        onClick={onZoomIn}
        disabled={!canZoomIn}
        aria-label={t("campaignHome.mapPreviewZoomIn")}
        className="flex h-6 w-6 items-center justify-center rounded-full text-sm font-bold text-slate-200 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
      >
        +
      </button>
    </div>
  );
};
