import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { characterSheetDraftsRepo } from "../../shared/api/characterSheetDraftsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import type { PartyCharacterSheetDraftRecord } from "../../entities/character";
import type { PartyDetailsPlayerResource } from "./usePartyDetailsResources";

type Props = {
  drafts: PartyCharacterSheetDraftRecord[];
  loading: boolean;
  partyId: string;
  players: PartyDetailsPlayerResource[];
  onChanged: () => Promise<void>;
};

export const PartyDetailsCharacterSheetDraftsCard = ({
  drafts,
  loading,
  partyId,
  players,
  onChanged,
}: Props) => {
  const navigate = useNavigate();
  const { t } = useLocale();
  const [busyDraftId, setBusyDraftId] = useState<string | null>(null);
  const [deriveDraftId, setDeriveDraftId] = useState<string | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>("");
  const [creating, setCreating] = useState(false);

  const activeDrafts = useMemo(
    () => drafts.filter((draft) => draft.status === "active"),
    [drafts],
  );
  const archivedDrafts = useMemo(
    () => drafts.filter((draft) => draft.status === "archived"),
    [drafts],
  );
  const eligiblePlayers = useMemo(
    () => players.filter((player) => player.sheetStatus === "missing"),
    [players],
  );
  const deriveDisabled = eligiblePlayers.length === 0;

  const handleCreateDraft = async () => {
    if (creating) return;
    setCreating(true);
    try {
      navigate(
        routes.gmPartyCharacterSheetDraftNew.replace(":partyId", partyId),
      );
    } finally {
      setCreating(false);
    }
  };

  const handleDraftAction = async (
    draftId: string,
    action: () => Promise<unknown>,
  ) => {
    setBusyDraftId(draftId);
    try {
      await action();
      await onChanged();
    } catch (error) {
      alert((error as { message?: string })?.message ?? "Failed to update draft.");
    } finally {
      setBusyDraftId(null);
    }
  };

  const openDraft = (draftId: string) => {
    navigate(
      routes.gmPartyCharacterSheetDraft
        .replace(":partyId", partyId)
        .replace(":draftId", draftId),
    );
  };

  const confirmDerive = async () => {
    if (!deriveDraftId || !selectedPlayerId) return;
    setBusyDraftId(deriveDraftId);
    try {
      await characterSheetDraftsRepo.derive(partyId, deriveDraftId, selectedPlayerId);
      setDeriveDraftId(null);
      setSelectedPlayerId("");
      await onChanged();
    } catch (error) {
      alert((error as { message?: string })?.message ?? "Failed to derive draft.");
    } finally {
      setBusyDraftId(null);
    }
  };

  return (
    <div className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.95))] p-6">
      <div className="flex flex-col gap-4 border-b border-white/8 pb-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-300">
            {t("gm.party.draftsTitle")}
          </p>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            {t("gm.party.draftsDescription")}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleCreateDraft()}
          disabled={creating}
          className={`rounded-full px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] ${
            creating
              ? "cursor-wait border border-white/8 bg-white/4 text-slate-500"
              : "border border-emerald-400/20 bg-emerald-400/10 text-emerald-100 transition hover:bg-emerald-400/20"
          }`}
        >
          {creating ? t("gm.party.creatingDraft") : t("gm.party.createDraft")}
        </button>
      </div>

      <div className="mt-5 space-y-5">
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("gm.party.activeDrafts")}
            </p>
            <span className="text-xs text-slate-500">{activeDrafts.length}</span>
          </div>
          {loading ? (
            <p className="text-sm text-slate-400">{t("gm.party.loadingResources")}</p>
          ) : activeDrafts.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-white/8 px-4 py-4 text-sm text-slate-500">
              {t("gm.party.noDrafts")}
            </p>
          ) : (
            activeDrafts.map((draft) => (
              <article
                key={draft.id}
                className="rounded-3xl border border-white/8 bg-white/3 p-4"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-base font-semibold text-white">{draft.name}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {draft.lastDerivedAt
                        ? t("gm.party.draftLastDerived").replace("{date}", new Date(draft.lastDerivedAt).toLocaleDateString())
                        : t("gm.party.draftBlank")}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => openDraft(draft.id)}
                      className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-100 transition hover:bg-cyan-400/20"
                    >
                      {t("gm.party.openDraft")}
                    </button>
                    <button
                      type="button"
                      disabled={busyDraftId === draft.id || deriveDisabled}
                      onClick={() => {
                        setDeriveDraftId(draft.id);
                        setSelectedPlayerId(eligiblePlayers[0]?.userId ?? "");
                      }}
                      className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${
                        busyDraftId === draft.id || deriveDisabled
                          ? "cursor-not-allowed border border-white/8 bg-white/4 text-slate-500"
                          : "border border-emerald-400/20 bg-emerald-400/10 text-emerald-100 transition hover:bg-emerald-400/20"
                      }`}
                    >
                      {t("gm.party.deriveDraft")}
                    </button>
                    <button
                      type="button"
                      disabled={busyDraftId === draft.id}
                      onClick={() =>
                        void handleDraftAction(draft.id, () =>
                          characterSheetDraftsRepo.archive(partyId, draft.id),
                        )
                      }
                      className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-100 transition hover:bg-amber-400/20 disabled:cursor-not-allowed disabled:text-slate-500"
                    >
                      {t("gm.party.archiveDraft")}
                    </button>
                    <button
                      type="button"
                      disabled={busyDraftId === draft.id}
                      onClick={() => {
                        if (!confirm(t("gm.party.deleteDraftConfirm"))) {
                          return;
                        }
                        void handleDraftAction(draft.id, () =>
                          characterSheetDraftsRepo.remove(partyId, draft.id),
                        );
                      }}
                      className="rounded-full border border-rose-400/20 bg-rose-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-rose-100 transition hover:bg-rose-400/20 disabled:cursor-not-allowed disabled:text-slate-500"
                    >
                      {t("gm.party.deleteDraft")}
                    </button>
                  </div>
                </div>
              </article>
            ))
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("gm.party.archivedDrafts")}
            </p>
            <span className="text-xs text-slate-500">{archivedDrafts.length}</span>
          </div>
          {archivedDrafts.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-white/8 px-4 py-4 text-sm text-slate-500">
              {t("gm.party.noArchivedDrafts")}
            </p>
          ) : (
            archivedDrafts.map((draft) => (
              <article
                key={draft.id}
                className="rounded-3xl border border-white/8 bg-white/3 p-4 opacity-85"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-base font-semibold text-white">{draft.name}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {draft.archivedAt
                        ? t("gm.party.draftArchivedAt").replace("{date}", new Date(draft.archivedAt).toLocaleDateString())
                        : t("gm.party.draftArchived")}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => openDraft(draft.id)}
                      className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-100 transition hover:bg-cyan-400/20"
                    >
                      {t("gm.party.openDraft")}
                    </button>
                    <button
                      type="button"
                      disabled={busyDraftId === draft.id}
                      onClick={() =>
                        void handleDraftAction(draft.id, () =>
                          characterSheetDraftsRepo.restore(partyId, draft.id),
                        )
                      }
                      className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-100 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:text-slate-500"
                    >
                      {t("gm.party.restoreDraft")}
                    </button>
                    <button
                      type="button"
                      disabled={busyDraftId === draft.id}
                      onClick={() => {
                        if (!confirm(t("gm.party.deleteDraftConfirm"))) {
                          return;
                        }
                        void handleDraftAction(draft.id, () =>
                          characterSheetDraftsRepo.remove(partyId, draft.id),
                        );
                      }}
                      className="rounded-full border border-rose-400/20 bg-rose-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-rose-100 transition hover:bg-rose-400/20 disabled:cursor-not-allowed disabled:text-slate-500"
                    >
                      {t("gm.party.deleteDraft")}
                    </button>
                  </div>
                </div>
              </article>
            ))
          )}
        </section>
      </div>

      {deriveDraftId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
          <div className="w-full max-w-lg rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.98),rgba(2,6,23,0.98))] p-6 shadow-[0_24px_80px_rgba(2,6,23,0.48)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-emerald-300">
              {t("gm.party.deriveDraft")}
            </p>
            <p className="mt-3 text-sm leading-7 text-slate-300">
              {eligiblePlayers.length > 0
                ? t("gm.party.deriveDescription")
                : t("gm.party.noEligiblePlayers")}
            </p>

            <label className="mt-5 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
              {t("gm.party.deriveTargetLabel")}
            </label>
            <select
              value={selectedPlayerId}
              onChange={(event) => setSelectedPlayerId(event.target.value)}
              disabled={eligiblePlayers.length === 0}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-emerald-300/35"
            >
              {eligiblePlayers.length === 0 ? (
                <option value="">{t("gm.party.noEligiblePlayers")}</option>
              ) : (
                eligiblePlayers.map((player) => (
                  <option key={player.userId} value={player.userId}>
                    {player.displayName}
                  </option>
                ))
              )}
            </select>

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setDeriveDraftId(null);
                  setSelectedPlayerId("");
                }}
                className="rounded-full border border-white/10 bg-white/4 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-200 transition hover:bg-white/8"
              >
                {t("gm.home.campaignCancel")}
              </button>
              <button
                type="button"
                disabled={!selectedPlayerId || busyDraftId === deriveDraftId}
                onClick={() => void confirmDerive()}
                className={`rounded-full px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] ${
                  !selectedPlayerId || busyDraftId === deriveDraftId
                    ? "cursor-not-allowed border border-white/10 bg-white/4 text-slate-500"
                    : "border border-emerald-400/20 bg-emerald-400/10 text-emerald-100 transition hover:bg-emerald-400/20"
                }`}
              >
                {busyDraftId === deriveDraftId
                  ? t("gm.party.derivingDraft")
                  : t("gm.party.confirmDerive")}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
