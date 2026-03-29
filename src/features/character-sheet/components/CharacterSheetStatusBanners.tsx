import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  isPlay: boolean;
  isSheetLocked: boolean;
  isDraftArchived?: boolean;
  isPendingAcceptance?: boolean;
  showAcceptPendingSheetAction?: boolean;
  canAcceptPendingSheet?: boolean;
  acceptingPendingSheet?: boolean;
  acceptPendingSheetError?: string | null;
  onAcceptPendingSheet?: () => void;
  playContextLabel?: string | null;
};

export const CharacterSheetStatusBanners = ({
  isPlay,
  isSheetLocked,
  isDraftArchived = false,
  isPendingAcceptance = false,
  showAcceptPendingSheetAction = false,
  canAcceptPendingSheet = false,
  acceptingPendingSheet = false,
  acceptPendingSheetError = null,
  onAcceptPendingSheet,
  playContextLabel,
}: Props) => {
  const { t } = useLocale();

  return (
    <>
      {isDraftArchived && (
        <div className="rounded-[28px] border border-amber-400/25 bg-amber-400/10 px-5 py-4 shadow-[0_16px_40px_rgba(245,158,11,0.12)]">
          <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-amber-300">
            {t("sheet.status.draftArchivedEyebrow")}
          </p>
          <p className="mt-2 text-sm text-amber-50/90">
            {t("sheet.status.draftArchivedBody")}
          </p>
        </div>
      )}

      {isPendingAcceptance && (
        <div className="rounded-[28px] border border-emerald-400/20 bg-emerald-400/10 px-5 py-4 shadow-[0_16px_40px_rgba(16,185,129,0.12)]">
          <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-emerald-300">
            {t("sheet.status.pendingAcceptanceEyebrow")}
          </p>
          <p className="mt-2 text-sm text-emerald-50/90">
            {showAcceptPendingSheetAction
              ? (
                  canAcceptPendingSheet
                    ? t("sheet.status.pendingAcceptanceBody")
                    : t("sheet.status.pendingAcceptanceLockedBody")
                )
              : t("sheet.status.pendingAcceptanceObserverBody")}
          </p>
          {showAcceptPendingSheetAction && canAcceptPendingSheet && onAcceptPendingSheet ? (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={onAcceptPendingSheet}
                disabled={acceptingPendingSheet}
                className={`rounded-full px-4 py-2 text-[11px] font-bold uppercase tracking-[0.22em] ${
                  acceptingPendingSheet
                    ? "cursor-wait border border-white/10 bg-white/5 text-slate-400"
                    : "border border-emerald-300/30 bg-emerald-300/15 text-emerald-100 transition hover:bg-emerald-300/20"
                }`}
              >
                {acceptingPendingSheet
                  ? t("sheet.status.acceptingAction")
                  : t("sheet.status.acceptAction")}
              </button>
              <span className="text-xs text-emerald-100/70">
                {t("sheet.status.acceptHint")}
              </span>
            </div>
          ) : null}
          {acceptPendingSheetError ? (
            <p className="mt-3 text-xs text-rose-200">{acceptPendingSheetError}</p>
          ) : null}
        </div>
      )}

      {isSheetLocked && (
        <div className="rounded-2xl border border-slate-700/50 bg-slate-900/60 px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 shrink-0 rounded-full bg-slate-500" />
            <p className="text-sm text-slate-400">
              {t("sheet.status.lockedBody")}
            </p>
          </div>
        </div>
      )}

      {isPlay && playContextLabel && (
        <div className="rounded-[28px] border border-sky-400/20 bg-sky-400/10 px-5 py-4 shadow-[0_16px_40px_rgba(14,165,233,0.12)]">
          <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-sky-300">
            {t("sheet.status.gmPlayEyebrow")}
          </p>
          <p className="mt-2 text-sm text-slate-100">
            {t("sheet.status.gmPlayBodyStart")}{" "}
            <span className="font-semibold text-sky-200">{playContextLabel}</span>
            {t("sheet.status.gmPlayBodyEnd")}
          </p>
        </div>
      )}
    </>
  );
};
