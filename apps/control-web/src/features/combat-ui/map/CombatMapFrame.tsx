import { useEffect, useMemo, useRef, useState } from "react";
import { combatRepo, type CombatActiveAreaEffect } from "../../../shared/api/combatRepo";
import type { SpellMapHighlight } from "./combatMapHighlight.types";

export type CombatMapSelectionMode = "none" | "select-token" | "select-cell";

type Coordinate = {
  x: number;
  y: number;
};

type MapActorContext = {
  actorId: string;
  actorType: "player" | "gm";
};

export type CombatMapFrameActiveAreaEffect = {
  id: string;
  sourceSpellCanonicalKey?: string | null;
  sourceSpellName: string;
  casterParticipantId: string;
  casterRefId?: string | null;
  casterCharacterId?: string | null;
  originPoint: Coordinate;
  anchorCell: Coordinate;
  areaShape: "sphere" | "cone" | "line" | "cube" | "cylinder";
  sizeMeters: number;
  radiusMeters?: number | null;
  lengthMeters?: number | null;
  sideMeters?: number | null;
  affectedCells: Coordinate[];
  effectKind: string;
  duration?: string | null;
  concentrationOwnerParticipantId?: string | null;
  concentrationOwnerRefId?: string | null;
  createdRound?: number | null;
  createdTurnIndex?: number | null;
  obscurement?: string | null;
  terrainEffect?: string | null;
  movementDamageDice?: string | null;
  damageType?: string | null;
  damagePerMeters?: number | null;
};

export const toCombatMapFrameAreaEffects = (
  effects?: CombatActiveAreaEffect[] | null,
): CombatMapFrameActiveAreaEffect[] =>
  (effects ?? []).map((effect) => ({
    id: effect.id,
    sourceSpellCanonicalKey: effect.source_spell_canonical_key,
    sourceSpellName: effect.source_spell_name,
    casterParticipantId: effect.caster_participant_id,
    casterRefId: effect.caster_ref_id,
    casterCharacterId: effect.caster_character_id,
    originPoint: effect.origin_point,
    anchorCell: effect.anchor_cell,
    areaShape: effect.area_shape,
    sizeMeters: effect.size_meters,
    radiusMeters: effect.radius_meters,
    lengthMeters: effect.length_meters,
    sideMeters: effect.side_meters,
    affectedCells: effect.affected_cells ?? [],
    effectKind: effect.effect_kind,
    duration: effect.duration,
    concentrationOwnerParticipantId: effect.concentration_owner_participant_id,
    concentrationOwnerRefId: effect.concentration_owner_ref_id,
    createdRound: effect.created_round,
    createdTurnIndex: effect.created_turn_index,
    obscurement: effect.obscurement,
    terrainEffect: effect.terrain_effect,
    movementDamageDice: effect.movement_damage_dice,
    damageType: effect.damage_type,
    damagePerMeters: effect.damage_per_meters,
  }));

export type CombatMapTokenSelection = {
  tokenId: string;
  combatantId: string | null;
  label: string;
  position: Coordinate;
};

export type CombatMapCellSelection = {
  cell: Coordinate;
  tokenId: string | null;
  combatantId: string | null;
};

export type { SpellMapHighlight };

type Props = {
  sessionId: string;
  title: string;
  hint: string;
  combatPhase?: string | null;
  actor?: MapActorContext | null;
  selectionMode?: CombatMapSelectionMode;
  previewCells?: Coordinate[];
  activeAreaEffects?: CombatMapFrameActiveAreaEffect[];
  selectedCell?: Coordinate | null;
  selectedTargetRefId?: string | null;
  spellHighlights?: SpellMapHighlight[];
  className?: string;
  frameClassName?: string;
  onCellSelected?: (selection: CombatMapCellSelection) => void;
  onCellHovered?: (selection: CombatMapCellSelection | null) => void;
  onTokenSelected?: (selection: CombatMapTokenSelection) => void;
};

const stripTrailingSlash = (value: string) => value.replace(/\/+$/, "");

const resolveMapWebBaseUrl = () => {
  const configured = import.meta.env.VITE_MAP_WEB_URL?.trim();
  if (configured) {
    return stripTrailingSlash(configured);
  }

  if (typeof window !== "undefined") {
    const nextUrl = new URL(window.location.href);
    nextUrl.port = "5174";
    nextUrl.pathname = "/";
    nextUrl.search = "";
    nextUrl.hash = "";
    return stripTrailingSlash(nextUrl.toString());
  }

  return "http://localhost:5174";
};

const buildMapFrameUrl = (sessionId: string) => {
  const nextUrl = new URL(resolveMapWebBaseUrl());
  nextUrl.searchParams.set("sessionId", sessionId);
  nextUrl.searchParams.set("embedded", "1");
  return nextUrl.toString();
};

const resolveBootstrapMessage = (reason?: string | null) => {
  switch (reason) {
    case "combat_not_active":
      return "O mapa tatico fica disponivel quando o combate estiver ativo.";
    case "combat_not_found":
      return "O combate desta sessao ainda nao foi iniciado.";
    case "limiar_map_disabled":
      return "A integracao do mapa tatico esta desativada neste ambiente.";
    case "no_combatants":
      return "Nao foi possivel sincronizar o mapa porque o combate nao possui participantes validos.";
    default:
      return "Nao foi possivel preparar o mapa tatico desta sessao.";
  }
};

export const CombatMapFrame = ({
  sessionId,
  title,
  hint,
  combatPhase = null,
  actor = null,
  selectionMode = "none",
  previewCells = [],
  activeAreaEffects = [],
  selectedCell = null,
  selectedTargetRefId = null,
  spellHighlights = [],
  className,
  frameClassName,
  onCellSelected,
  onCellHovered,
  onTokenSelected,
}: Props) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [frameLoaded, setFrameLoaded] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const [bootstrapNonce, setBootstrapNonce] = useState(0);
  const [bootstrapState, setBootstrapState] = useState<{
    status: "preparing" | "ready" | "unavailable" | "error";
    message?: string;
  }>({ status: "preparing" });
  const frameUrl = useMemo(() => buildMapFrameUrl(sessionId), [sessionId]);

  const postContext = () => {
    const targetWindow = iframeRef.current?.contentWindow;
    if (!targetWindow) {
      return;
    }

    targetWindow.postMessage(
      {
        type: "limiar-control:map-context",
        payload: {
          sessionId,
          actor,
          selectionMode,
          previewCells,
          activeAreaEffects,
          selectedCell,
          selectedTargetRefId,
          combatPhase,
          spellHighlights,
        },
      },
      "*",
    );
  };

  useEffect(() => {
    setFrameLoaded(false);
    setMapReady(false);
  }, [frameUrl, bootstrapNonce]);

  useEffect(() => {
    let cancelled = false;

    setBootstrapState({ status: "preparing" });
    setFrameLoaded(false);
    setMapReady(false);

    combatRepo
      .ensureMap(sessionId)
      .then((result) => {
        if (cancelled) {
          return;
        }

        if (result.map_available) {
          setBootstrapState({ status: "ready" });
          return;
        }

        setBootstrapState({
          status: "unavailable",
          message: resolveBootstrapMessage(result.reason),
        });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }

        setBootstrapState({
          status: "error",
          message:
            error instanceof Error && error.message
              ? error.message
              : "Nao foi possivel preparar o mapa tatico.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [bootstrapNonce, combatPhase, sessionId]);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow) {
        return;
      }

      const data = event.data as
        | {
            type?: string;
            payload?: Record<string, unknown>;
          }
        | null;

      if (!data || typeof data !== "object") {
        return;
      }

      if (data.type === "limiar-map:ready") {
        if (data.payload?.sessionId !== sessionId) {
          return;
        }
        setMapReady(true);
        postContext();
        return;
      }

      if (data.type === "limiar-map:token-selected") {
        if (!onTokenSelected || data.payload?.sessionId !== sessionId) {
          return;
        }
        const tokenId = data.payload.tokenId;
        const label = data.payload.label;
        const combatantId = data.payload.combatantId;
        const position = data.payload.position as Coordinate | undefined;
        if (
          typeof tokenId !== "string" ||
          typeof label !== "string" ||
          !position ||
          typeof position.x !== "number" ||
          typeof position.y !== "number"
        ) {
          return;
        }
        onTokenSelected({
          tokenId,
          label,
          combatantId: typeof combatantId === "string" ? combatantId : null,
          position,
        });
        return;
      }

      if (data.type === "limiar-map:cell-selected") {
        if (!onCellSelected || data.payload?.sessionId !== sessionId) {
          return;
        }
        const cell = data.payload.cell as Coordinate | undefined;
        if (!cell || typeof cell.x !== "number" || typeof cell.y !== "number") {
          return;
        }
        onCellSelected({
          cell,
          tokenId: typeof data.payload.tokenId === "string" ? data.payload.tokenId : null,
          combatantId:
            typeof data.payload.combatantId === "string" ? data.payload.combatantId : null,
        });
        return;
      }

      if (data.type === "limiar-map:cell-hovered") {
        if (!onCellHovered || data.payload?.sessionId !== sessionId) {
          return;
        }
        const cell = data.payload.cell as Coordinate | null | undefined;
        if (cell == null) {
          onCellHovered(null);
          return;
        }
        if (typeof cell.x !== "number" || typeof cell.y !== "number") {
          return;
        }
        onCellHovered({
          cell,
          tokenId: typeof data.payload.tokenId === "string" ? data.payload.tokenId : null,
          combatantId:
            typeof data.payload.combatantId === "string" ? data.payload.combatantId : null,
        });
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [onCellHovered, onCellSelected, onTokenSelected, sessionId]);

  useEffect(() => {
    if (bootstrapState.status !== "ready") {
      return;
    }
    if (!frameLoaded && !mapReady) {
      return;
    }
    postContext();
  }, [
    actor,
    bootstrapState.status,
    combatPhase,
    frameLoaded,
    mapReady,
    previewCells,
    activeAreaEffects,
    selectedCell,
    selectedTargetRefId,
    selectionMode,
    sessionId,
    spellHighlights,
  ]);

  return (
    <section
      className={
        className ??
        "rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.94))] p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]"
      }
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {title}
          </p>
          <p className="mt-2 text-sm leading-7 text-slate-300">{hint}</p>
        </div>
        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-300">
          {selectionMode === "select-token"
            ? t("combatUi.targeting")
            : selectionMode === "select-cell"
              ? t("combatUi.area")
              : t("combatUi.preview")}
        </span>
      </div>

      <div className="relative mt-4 overflow-hidden rounded-3xl border border-white/8 bg-slate-950/70">
        {bootstrapState.status === "ready" ? (
          <iframe
            key={`${sessionId}:${bootstrapNonce}`}
            ref={iframeRef}
            title={title}
            src={frameUrl}
            onLoad={() => {
              setFrameLoaded(true);
              postContext();
            }}
            className={frameClassName ?? "h-[520px] w-full border-0 bg-slate-950"}
          />
        ) : (
          <div className={frameClassName ?? "flex h-[520px] w-full items-center justify-center bg-slate-950"} />
        )}

        {bootstrapState.status === "preparing" ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-950/55 text-sm font-medium text-slate-200 backdrop-blur-sm">
            Preparando mapa tatico...
          </div>
        ) : null}

        {bootstrapState.status === "ready" && !mapReady ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-950/55 text-sm font-medium text-slate-200 backdrop-blur-sm">
            Carregando mapa tatico...
          </div>
        ) : null}

        {bootstrapState.status !== "preparing" && bootstrapState.status !== "ready" ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/70 p-6 backdrop-blur-sm">
            <div className="max-w-md rounded-3xl border border-rose-400/30 bg-rose-500/10 px-5 py-4 text-center text-sm leading-7 text-rose-100 shadow-[0_18px_50px_rgba(15,23,42,0.32)]">
              <p>{bootstrapState.message}</p>
              <button
                type="button"
                onClick={() => {
                  setBootstrapNonce((current) => current + 1);
                }}
                className="mt-4 inline-flex items-center justify-center rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white transition hover:bg-white/15"
              >
                Tentar novamente
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
};
