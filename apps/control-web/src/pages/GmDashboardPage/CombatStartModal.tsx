import { useState } from "react";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { SessionEntity } from "../../entities/session-entity/sessionEntity.types";
import { useLocale } from "../../shared/hooks/useLocale";
import type { CampaignMapConfig } from "../../entities/campaign";
import { ManagedImage } from "../../shared/ui/ManagedImage";

type CombatParticipantPreview = {
  id: string;
  kind: "player" | "session_entity";
  displayName: string;
  included: boolean;
};

type CombatMapChoice =
  | { kind: "campaign_map"; mapId: string }
  | { kind: "demo_map"; mapId?: null };

type CombatStartSelection = {
  participants: CombatParticipantPreview[];
  selectedMap: CombatMapChoice;
};

type Props = {
  isOpen: boolean;
  loading: boolean;
  campaignMaps: CampaignMapConfig[];
  partyPlayers: PartyMemberSummary[];
  sessionEntities: SessionEntity[];
  onClose: () => void;
  onConfirm: (selection: CombatStartSelection) => void;
};

export type { CombatParticipantPreview, CombatStartSelection };

export const CombatStartModal = ({
  isOpen,
  loading,
  campaignMaps,
  partyPlayers,
  sessionEntities,
  onClose,
  onConfirm,
}: Props) => {
  const { t } = useLocale();
  const readyCampaignMaps = campaignMaps.filter(
    (map) => Boolean(map.imageUrl) && map.gridWidth != null && map.gridHeight != null,
  );

  const buildInitial = (): CombatParticipantPreview[] => [
    ...partyPlayers.map((p) => ({
      id: p.userId,
      kind: "player" as const,
      displayName: p.displayName || p.username || t("gm.dashboard.playerLabel"),
      included: true,
    })),
    ...sessionEntities.map((e) => ({
      id: e.id,
      kind: "session_entity" as const,
      displayName: e.label || e.entity?.name || t("gm.dashboard.entityLabel"),
      included: true,
    })),
  ];

  const [participants, setParticipants] = useState<CombatParticipantPreview[]>(buildInitial);
  const [selectedMap, setSelectedMap] = useState<CombatMapChoice | null>(null);

  // Rebuild when modal opens with new data
  const [lastOpen, setLastOpen] = useState(false);
  if (isOpen && !lastOpen) {
    setParticipants(buildInitial());
    setSelectedMap(null);
    setLastOpen(true);
  } else if (!isOpen && lastOpen) {
    setLastOpen(false);
  }

  if (!isOpen) return null;

  const toggle = (id: string) =>
    setParticipants((prev) =>
      prev.map((p) => (p.id === id ? { ...p, included: !p.included } : p)),
    );

  const players = participants.filter((p) => p.kind === "player");
  const entities = participants.filter((p) => p.kind === "session_entity");
  const anyIncluded = participants.some((p) => p.included);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
      <div className="w-full max-w-4xl rounded-3xl border border-slate-800 bg-void-950 p-6 shadow-2xl">
        <h2 className="text-xl font-semibold text-white">
          {t("gm.dashboard.combatStartTitle" as Parameters<typeof t>[0])}
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          {t("gm.dashboard.combatStartDescription" as Parameters<typeof t>[0])}
        </p>

        <div className="mt-5 max-h-80 space-y-4 overflow-y-auto pr-1">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
              {t("gm.dashboard.combatMapLabel" as Parameters<typeof t>[0])}
            </p>
            <div className="mt-2 grid gap-3 md:grid-cols-2">
              {readyCampaignMaps.map((map) => {
                const isSelected =
                  selectedMap?.kind === "campaign_map" && selectedMap.mapId === map.id;
                return (
                  <button
                    key={map.id}
                    type="button"
                    onClick={() => setSelectedMap({ kind: "campaign_map", mapId: map.id })}
                    className={`w-full rounded-2xl border p-3 text-left transition-all ${
                      isSelected
                        ? "border-limiar-400/60 bg-limiar-500/10"
                        : "border-slate-800/60 bg-slate-900/50 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex gap-3">
                      <div className="h-24 w-32 overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
                        {map.imageUrl ? (
                          <ManagedImage
                            src={map.imageUrl}
                            alt={map.mapName ?? t("gm.dashboard.campaignMap")}
                            className="h-full w-full object-cover"
                          />
                        ) : null}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-white">
                          {map.mapName ||
                            t("gm.dashboard.combatMapCampaign" as Parameters<typeof t>[0])}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                          {t("gm.dashboard.combatMapCampaignDescription" as Parameters<typeof t>[0])}
                        </p>
                        <p className="mt-2 text-[11px] text-slate-500">
                          {`${map.gridWidth ?? 0} x ${map.gridHeight ?? 0}`}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}

              <button
                type="button"
                onClick={() => setSelectedMap({ kind: "demo_map" })}
                className={`w-full rounded-2xl border p-3 text-left transition-all ${
                  selectedMap?.kind === "demo_map"
                    ? "border-amber-400/60 bg-amber-500/10"
                    : "border-slate-800/60 bg-slate-900/50 hover:border-slate-700"
                }`}
              >
                <p className="text-sm font-semibold text-white">
                  {t("gm.dashboard.combatMapDemo" as Parameters<typeof t>[0])}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {t("gm.dashboard.combatMapDemoDescription" as Parameters<typeof t>[0])}
                </p>
              </button>

              {readyCampaignMaps.length === 0 && (
                <p className="md:col-span-2 text-xs text-amber-300">
                  {t("gm.dashboard.combatMapUnavailable" as Parameters<typeof t>[0])}
                </p>
              )}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {players.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
                  {t("gm.dashboard.playersCount")}
                </p>
                <div className="mt-2 space-y-1.5">
                  {players.map((p) => (
                    <label
                      key={p.id}
                      className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 transition-all ${
                        p.included
                          ? "border-emerald-500/20 bg-emerald-500/10"
                          : "border-slate-800/40 bg-slate-900/40 opacity-50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={p.included}
                        onChange={() => toggle(p.id)}
                        className="accent-emerald-500"
                      />
                      <div className="flex h-7 w-7 items-center justify-center rounded-full border border-emerald-500/30 bg-emerald-500/20 text-xs font-bold text-emerald-300">
                        {p.displayName.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-sm font-medium text-slate-200">{p.displayName}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {entities.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
                  {t("gm.dashboard.combatEntitiesLabel" as Parameters<typeof t>[0])}
                </p>
                <div className="mt-2 space-y-1.5">
                  {entities.map((p) => (
                    <label
                      key={p.id}
                      className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 transition-all ${
                        p.included
                          ? "border-rose-500/20 bg-rose-500/10"
                          : "border-slate-800/40 bg-slate-900/40 opacity-50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={p.included}
                        onChange={() => toggle(p.id)}
                        className="accent-rose-500"
                      />
                      <div className="flex h-7 w-7 items-center justify-center rounded-full border border-rose-500/30 bg-rose-500/20 text-xs font-bold text-rose-300">
                        {p.displayName.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-sm font-medium text-slate-200">{p.displayName}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>

          {participants.length === 0 && (
            <p className="py-4 text-center text-sm text-slate-500">
              {t("gm.dashboard.combatNoParticipants" as Parameters<typeof t>[0])}
            </p>
          )}
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="flex-1 rounded-full border border-slate-700 px-4 py-2.5 text-sm font-semibold text-slate-300 hover:border-slate-500 disabled:opacity-50"
          >
            {t("common.close")}
          </button>
          <button
            type="button"
            onClick={() => {
              if (!selectedMap) {
                return;
              }
              onConfirm({
                participants: participants.filter((p) => p.included),
                selectedMap,
              });
            }}
            disabled={loading || !anyIncluded || !selectedMap}
            className="flex-1 rounded-full bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
          >
            {loading
              ? t("gm.dashboard.combatSyncing")
              : t("gm.dashboard.combatConfirmStart" as Parameters<typeof t>[0])}
          </button>
        </div>
      </div>
    </div>
  );
};
