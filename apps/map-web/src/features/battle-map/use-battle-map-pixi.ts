import { useEffect, useRef, useState } from "react";
import { Application, Sprite, Container, Graphics, Texture } from "pixi.js";
import type { EncounterSnapshotResponse } from "@limiarmap/shared-contracts";
import type { BattleMapUIState } from "./battle-map-store";
import type { GridEditInteraction } from "./types";
import { battleMapStore } from "./battle-map-store";
import { DEFAULT_MAP_IMAGE_URL, C } from "./constants";
import { applyGridCalibrationInteraction, canInteractWithToken } from "./utils";
import { findReachableCells } from "@limiarmap/tactical-engine";
import { attachPixiLayers, bindPixiStageEvents, buildDrawFunction, resetPixiRefs, type BattleMapPixiRefs } from "./battle-map-pixi-runtime";

type CurrentActor = { actorId: string; actorType: "player" | "gm" };

export function useBattleMapPixi(params: {
  encounter: EncounterSnapshotResponse | null;
  currentActor: CurrentActor;
  uiState: BattleMapUIState;
  selectedTokenId: string | null;
  setSelectedTokenId: React.Dispatch<React.SetStateAction<string | null>>;
  selectedToken: EncounterSnapshotResponse["tokens"][number] | null;
}): { containerRef: React.RefObject<HTMLDivElement | null>; imageAspectRatio: number } {
  const { encounter, currentActor, uiState, selectedTokenId, setSelectedTokenId, selectedToken } = params;
  const [imageAspectRatio, setImageAspectRatio] = useState(16 / 9);
  const [gridEditInteraction, setGridEditInteraction] = useState<GridEditInteraction | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const previewTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const drawRef = useRef<(() => void) | null>(null);
  const cbRef = useRef({ selectedTokenId, encounter, currentActor, uiState });
  const refs: BattleMapPixiRefs = {
    appRef: useRef<Application | null>(null),
    bgSpriteRef: useRef<Sprite | null>(null),
    backgroundUrlRef: useRef<string | null>(null),
    reachAoeGfxRef: useRef<Graphics | null>(null),
    gridGfxRef: useRef<Graphics | null>(null),
    cellFillsGfxRef: useRef<Graphics | null>(null),
    edgeObstaclesGfxRef: useRef<Graphics | null>(null),
    tokenContainerRef: useRef<Container | null>(null),
    tacticalOverlayContainerRef: useRef<Container | null>(null),
    editHandlesContainerRef: useRef<Container | null>(null),
    hudContainerRef: useRef<Container | null>(null),
  };

  useEffect(() => {
    cbRef.current = { selectedTokenId, encounter, currentActor, uiState };
  });

  useEffect(() => {
    let cancelled = false;
    async function init(): Promise<void> {
      if (!containerRef.current) return;
      const app = new Application();
      try {
        await app.init({ resizeTo: containerRef.current, background: C.bg, preference: "webgl", antialias: true, autoDensity: true, resolution: window.devicePixelRatio ?? 1 });
      } catch (error) {
        if (!cancelled) {
          console.error("[map-web] failed to initialize Pixi application", error);
          battleMapStore.setMessage("Nao foi possivel inicializar o renderer tatico do mapa.");
        }
        app.destroy(true);
        return;
      }
      if (cancelled) {
        app.destroy(true);
        return;
      }
      refs.appRef.current = app;
      containerRef.current.appendChild(app.canvas);
      attachPixiLayers(app, refs);
      bindPixiStageEvents(app, cbRef, previewTimerRef, setSelectedTokenId, setGridEditInteraction);
      drawRef.current = buildDrawFunction(refs, cbRef, setGridEditInteraction);
      app.renderer.on("resize", () => {
        if (refs.bgSpriteRef.current) {
          refs.bgSpriteRef.current.width = app.screen.width;
          refs.bgSpriteRef.current.height = app.screen.height;
        }
        app.stage.hitArea = app.screen;
        drawRef.current?.();
      });
      drawRef.current();
      const initialBgUrl = cbRef.current.encounter?.battleMap.imageUrl ?? DEFAULT_MAP_IMAGE_URL;
      if (refs.bgSpriteRef.current && refs.backgroundUrlRef.current !== initialBgUrl) {
        const img = new Image();
        img.decoding = "async";
        img.onload = () => {
          if (cancelled || !refs.bgSpriteRef.current) return;
          refs.backgroundUrlRef.current = initialBgUrl;
          refs.bgSpriteRef.current.texture = Texture.from(img);
          if (img.naturalWidth > 0 && img.naturalHeight > 0) {
            const ratio = img.naturalWidth / img.naturalHeight;
            setImageAspectRatio(ratio);
            battleMapStore.setMapImageAspectRatio(ratio);
            battleMapStore.setMapImageNaturalSize(img.naturalWidth, img.naturalHeight);
          }
          battleMapStore.setMessage(undefined);
          drawRef.current?.();
        };
        img.onerror = () => {
          if (!cancelled) battleMapStore.setMessage("Nao foi possivel carregar o background do mapa.");
        };
        img.src = initialBgUrl;
      }
    }
    void init();
    return () => {
      cancelled = true;
      drawRef.current = null;
      if (previewTimerRef.current) clearTimeout(previewTimerRef.current);
      if (refs.appRef.current) refs.appRef.current.destroy(true, { children: true });
      resetPixiRefs(refs);
    };
  }, []);

  useEffect(() => {
    drawRef.current?.();
  }, [encounter, uiState, selectedTokenId]);

  useEffect(() => {
    const nextBackgroundUrl = encounter?.battleMap.imageUrl ?? DEFAULT_MAP_IMAGE_URL;
    if (!refs.bgSpriteRef.current || refs.backgroundUrlRef.current === nextBackgroundUrl) return;
    let cancelled = false;
    const image = new Image();
    image.decoding = "async";
    image.onload = () => {
      if (cancelled || !refs.bgSpriteRef.current) return;
      refs.backgroundUrlRef.current = nextBackgroundUrl;
      refs.bgSpriteRef.current.texture = Texture.from(image);
      if (image.naturalWidth > 0 && image.naturalHeight > 0) {
        const ratio = image.naturalWidth / image.naturalHeight;
        setImageAspectRatio(ratio);
        battleMapStore.setMapImageAspectRatio(ratio);
        battleMapStore.setMapImageNaturalSize(image.naturalWidth, image.naturalHeight);
      }
      battleMapStore.setMessage(undefined);
      drawRef.current?.();
    };
    image.onerror = () => {
      if (!cancelled) battleMapStore.setMessage("Nao foi possivel carregar o background do mapa.");
    };
    image.src = nextBackgroundUrl;
    return () => {
      cancelled = true;
    };
  }, [encounter?.battleMap.imageUrl]);

  useEffect(() => {
    if (!gridEditInteraction || !encounter) return;
    const minWidth = 1 / (uiState.gridWidthDraft ?? encounter.battleMap.gridWidth);
    const minHeight = 1 / (uiState.gridHeightDraft ?? encounter.battleMap.gridHeight);
    function handleMove(event: PointerEvent): void {
      if (!containerRef.current) return;
      const interaction = gridEditInteraction;
      if (!interaction) return;
      const bounds = containerRef.current.getBoundingClientRect();
      if (bounds.width === 0 || bounds.height === 0) return;
      battleMapStore.updateGridCalibrationDraft(
        applyGridCalibrationInteraction(
          interaction,
          (event.clientX - interaction.startClientX) / bounds.width,
          (event.clientY - interaction.startClientY) / bounds.height,
          minWidth,
          minHeight,
        ),
      );
    }
    function handleUp(): void {
      setGridEditInteraction(null);
    }
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
    };
  }, [encounter, gridEditInteraction, uiState.gridHeightDraft, uiState.gridWidthDraft]);

  useEffect(() => {
    if (!encounter || !selectedTokenId) return;
    const token = encounter.tokens.find((item) => item.id === selectedTokenId);
    if (!token || !canInteractWithToken(currentActor, token, encounter.combatState)) setSelectedTokenId(null);
  }, [currentActor, encounter, selectedTokenId, setSelectedTokenId]);

  useEffect(() => {
    if ((uiState.isGridEditMode || uiState.isObstaclePaintMode) && selectedTokenId) setSelectedTokenId(null);
  }, [selectedTokenId, setSelectedTokenId, uiState.isGridEditMode, uiState.isObstaclePaintMode]);

  useEffect(() => {
    if (!selectedToken || !encounter) {
      battleMapStore.deactivateTacticalPreview();
      return;
    }
    battleMapStore.activateTacticalPreview(selectedToken.id, "move");
    battleMapStore.setTacticalPreviewReachableCells(
      findReachableCells({ map: encounter.battleMap, obstacles: encounter.obstacles, edgeObstacles: encounter.edgeObstacles, tokens: encounter.tokens }, selectedToken, encounter.combatState),
    );
  }, [encounter, selectedToken, selectedTokenId]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const publish = (): void => {
      const bounds = container.getBoundingClientRect();
      battleMapStore.setMapFrameSize(bounds.width, bounds.height);
    };
    publish();
    const observer = new ResizeObserver(publish);
    observer.observe(container);
    return () => observer.disconnect();
  }, [imageAspectRatio]);

  return { containerRef, imageAspectRatio };
}
