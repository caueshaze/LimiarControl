import React, { useEffect, useState, useSyncExternalStore } from "react";
import type { EncounterSnapshotResponse, GridCalibration } from "@limiarmap/shared-contracts";
import { MAX_GRID_DIMENSION } from "@limiarmap/shared-contracts";
import { useEncounterSnapshot } from "../../services/session-store";
import { useCurrentActor } from "../../services/centrifugo-client";
import { battleMapStore, type BattleMapUIState } from "./battle-map-store";
import { submitGridCalibration } from "./use-grid-calibration-actions";
import { deriveGridCalibrationFromTwoPoints } from "./utils";

const panelStyle: React.CSSProperties = {
  background: "#101725",
  border: "1px solid #24324a",
  borderRadius: 6,
  padding: 12,
  display: "flex",
  flexDirection: "column",
  gap: 8
};

const buttonStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 4,
  border: "1px solid",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer"
};

const numberInputStyle: React.CSSProperties = {
  width: 96,
  height: 36,
  borderRadius: 4,
  border: "1px solid rgba(110,160,220,0.35)",
  background: "rgba(8,16,28,0.9)",
  color: "#d8e6ff",
  fontSize: 14,
  fontWeight: 600,
  padding: "0 10px"
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function getCellWidthPx(
  gridCalibration: GridCalibration,
  gridWidth: number,
  sourceWidthPx: number
): number {
  return (gridCalibration.width * sourceWidthPx) / gridWidth;
}

function getCellHeightPx(
  gridCalibration: GridCalibration,
  gridHeight: number,
  sourceHeightPx: number
): number {
  return (gridCalibration.height * sourceHeightPx) / gridHeight;
}

function getMinimumGridDimensions(
  encounter: EncounterSnapshotResponse
): { gridWidth: number; gridHeight: number } {
  let gridWidth = 1;
  let gridHeight = 1;

  encounter.tokens.forEach((token) => {
    gridWidth = Math.max(gridWidth, token.position.x + 1);
    gridHeight = Math.max(gridHeight, token.position.y + 1);
  });

  encounter.obstacles.forEach((obstacle) => {
    obstacle.cells.forEach((cell) => {
      gridWidth = Math.max(gridWidth, cell.x + 1);
      gridHeight = Math.max(gridHeight, cell.y + 1);
    });
  });

  return { gridWidth, gridHeight };
}

function deriveGridDimension(
  calibrationSize: number,
  sourceSizePx: number,
  desiredCellSizePx: number,
  minimumDimension: number
): number {
  const coveredSizePx = calibrationSize * sourceSizePx;
  const desiredDimension = Math.round(coveredSizePx / desiredCellSizePx);
  return clamp(desiredDimension, minimumDimension, MAX_GRID_DIMENSION);
}

export function GridCalibrationPanel(): React.JSX.Element | null {
  const encounter = useEncounterSnapshot();
  const currentActor = useCurrentActor();
  const uiState = useSyncExternalStore(
    (listener) => battleMapStore.subscribe(listener),
    () => battleMapStore.getState(),
    () => battleMapStore.getState()
  );

  useEffect(() => {
    if (currentActor.actorType !== "gm" && uiState.isGridEditMode) {
      battleMapStore.cancelGridEdit();
    }
  }, [currentActor.actorType, uiState.isGridEditMode]);

  const gridCalibration = encounter?.battleMap.gridCalibration;
  if (!encounter || currentActor.actorType !== "gm" || !gridCalibration) {
    return null;
  }

  return (
    <GridCalibrationEditor
      encounter={encounter}
      gridCalibration={gridCalibration}
      uiState={uiState}
    />
  );
}

interface GridCalibrationEditorProps {
  encounter: EncounterSnapshotResponse;
  gridCalibration: GridCalibration;
  uiState: BattleMapUIState;
}

function GridCalibrationEditor({
  encounter,
  gridCalibration,
  uiState
}: GridCalibrationEditorProps): React.JSX.Element {
  const [cellInputs, setCellInputs] = useState({ width: "", height: "" });
  const [twoPointInputs, setTwoPointInputs] = useState({ x: "", y: "" });
  const draft = uiState.gridCalibrationDraft ?? gridCalibration;
  const draftGridWidth = uiState.gridWidthDraft ?? encounter.battleMap.gridWidth;
  const draftGridHeight = uiState.gridHeightDraft ?? encounter.battleMap.gridHeight;
  const isSaving = Boolean(uiState.pendingGridCalibrationActionId);
  const sourceWidthPx = uiState.mapImageNaturalWidthPx || uiState.mapFrameWidthPx;
  const sourceHeightPx = uiState.mapImageNaturalHeightPx || uiState.mapFrameHeightPx;
  const canAdjustCellSize = sourceWidthPx > 0 && sourceHeightPx > 0;
  const canUseTwoPointCalibration = canAdjustCellSize;
  const minimumGridDimensions = getMinimumGridDimensions(encounter);
  const currentCellWidthPx = getCellWidthPx(draft, draftGridWidth, sourceWidthPx);
  const currentCellHeightPx = getCellHeightPx(draft, draftGridHeight, sourceHeightPx);
  const hasFirstPoint = Boolean(uiState.twoPointCalibrationFirstPoint);
  const hasSecondPoint = Boolean(uiState.twoPointCalibrationSecondPoint);

  useEffect(() => {
    if (!canAdjustCellSize) {
      setCellInputs({ width: "", height: "" });
      return;
    }

    setCellInputs({
      width: currentCellWidthPx.toFixed(1),
      height: currentCellHeightPx.toFixed(1)
    });
  }, [canAdjustCellSize, currentCellHeightPx, currentCellWidthPx]);

  useEffect(() => {
    if (!uiState.isTwoPointCalibrationMode) {
      setTwoPointInputs({ x: "", y: "" });
    }
  }, [uiState.isTwoPointCalibrationMode]);

  function applyCellSize(nextWidthValue: string, nextHeightValue: string): void {
    if (!canAdjustCellSize) {
      return;
    }

    const parsedWidth = Number(nextWidthValue.replace(",", "."));
    const parsedHeight = Number(nextHeightValue.replace(",", "."));
    if (!Number.isFinite(parsedWidth) || parsedWidth <= 0) {
      return;
    }

    if (!Number.isFinite(parsedHeight) || parsedHeight <= 0) {
      return;
    }

    battleMapStore.setGridDimensionsDraft(
      deriveGridDimension(draft.width, sourceWidthPx, parsedWidth, minimumGridDimensions.gridWidth),
      deriveGridDimension(draft.height, sourceHeightPx, parsedHeight, minimumGridDimensions.gridHeight)
    );
  }

  function applyTwoPointCalibration(): void {
    if (
      !uiState.twoPointCalibrationFirstPoint ||
      !uiState.twoPointCalibrationSecondPoint ||
      !canUseTwoPointCalibration
    ) {
      return;
    }

    const squaresX = Number(twoPointInputs.x);
    const squaresY = Number(twoPointInputs.y);
    if (!Number.isInteger(squaresX) || squaresX <= 0 || !Number.isInteger(squaresY) || squaresY <= 0) {
      battleMapStore.setMessage("Informe quantidades inteiras positivas de celulas entre os pontos.");
      return;
    }

    try {
      const result = deriveGridCalibrationFromTwoPoints(
        uiState.twoPointCalibrationFirstPoint,
        uiState.twoPointCalibrationSecondPoint,
        squaresX,
        squaresY,
        sourceWidthPx,
        sourceHeightPx
      );
      battleMapStore.updateGridCalibrationDraft(result.gridCalibration);
      battleMapStore.setGridDimensionsDraft(result.gridWidth, result.gridHeight);
      battleMapStore.cancelTwoPointGridCalibration();
    } catch {
      battleMapStore.setMessage("Nao foi possivel calcular a calibracao com os dois pontos escolhidos.");
    }
  }

  const cellWidthInput = cellInputs.width;
  const cellHeightInput = cellInputs.height;
  const twoPointStatus = !uiState.isTwoPointCalibrationMode
    ? "Use dois cruzamentos confiaveis do grid para calcular o retangulo calibrado."
    : !hasFirstPoint
      ? "Clique no primeiro cruzamento do grid no canvas."
      : !hasSecondPoint
        ? "Clique em um segundo cruzamento distante no canvas."
        : "Informe quantas celulas existem entre os dois pontos em X e Y.";

  return (
    <section style={panelStyle}>
      <div
        style={{
          fontSize: 9,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          color: "#5f7ca3"
        }}
      >
        Grid do mapa
      </div>

      {!uiState.isGridEditMode ? (
        <>
          <button
            type="button"
            onClick={() =>
              battleMapStore.startGridEdit(
                gridCalibration,
                encounter.battleMap.gridWidth,
                encounter.battleMap.gridHeight
              )
            }
            style={{
              ...buttonStyle,
              background: "rgba(56,132,255,0.15)",
              borderColor: "rgba(90,160,255,0.4)",
              color: "#8cbcff"
            }}
          >
            Editar grid
          </button>

          <div style={{ fontSize: 11, color: "#6f86a6", lineHeight: 1.5 }}>
            O mestre pode alinhar o grid sobre a imagem e publicar o resultado para todos.
          </div>
        </>
      ) : (
        <>
          <div style={{ fontSize: 11, color: "#d9e7ff", lineHeight: 1.5 }}>
            Arraste o retangulo do grid no mapa para definir a area. `X × Y` ajusta quantas colunas
            e linhas cabem dentro dela.
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 8,
              background: "rgba(20,30,46,0.75)",
              border: "1px solid rgba(55,82,116,0.6)",
              borderRadius: 6,
              padding: "8px 10px"
            }}
          >
            <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color: "#7892b6" }}>
              Calibrar com 2 pontos
            </div>
            <div style={{ fontSize: 11, color: "#d8e6ff", lineHeight: 1.5 }}>
              {twoPointStatus}
            </div>
            <div style={{ fontSize: 11, color: "#7d94b8", lineHeight: 1.5 }}>
              Os dois pontos definem o retangulo calibrado. As celulas em X/Y representam apenas a area entre esses pontos.
            </div>
            {!uiState.isTwoPointCalibrationMode ? (
              <button
                type="button"
                disabled={isSaving || !canUseTwoPointCalibration}
                onClick={() => battleMapStore.startTwoPointGridCalibration()}
                style={{
                  ...buttonStyle,
                  background: "rgba(56,132,255,0.15)",
                  borderColor: "rgba(90,160,255,0.4)",
                  color: "#8cbcff",
                  cursor: isSaving || !canUseTwoPointCalibration ? "not-allowed" : "pointer",
                  opacity: isSaving || !canUseTwoPointCalibration ? 0.5 : 1
                }}
              >
                Calibrar com 2 pontos
              </button>
            ) : (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input
                    type="number"
                    inputMode="numeric"
                    min="1"
                    step="1"
                    disabled={isSaving || !hasSecondPoint}
                    value={twoPointInputs.x}
                    placeholder="Celulas entre os pontos — X"
                    onChange={(event) =>
                      setTwoPointInputs((current) => ({ ...current, x: event.currentTarget.value }))
                    }
                    style={{
                      ...numberInputStyle,
                      width: "100%",
                      opacity: isSaving || !hasSecondPoint ? 0.5 : 1
                    }}
                  />
                  <input
                    type="number"
                    inputMode="numeric"
                    min="1"
                    step="1"
                    disabled={isSaving || !hasSecondPoint}
                    value={twoPointInputs.y}
                    placeholder="Celulas entre os pontos — Y"
                    onChange={(event) =>
                      setTwoPointInputs((current) => ({ ...current, y: event.currentTarget.value }))
                    }
                    style={{
                      ...numberInputStyle,
                      width: "100%",
                      opacity: isSaving || !hasSecondPoint ? 0.5 : 1
                    }}
                  />
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    disabled={isSaving || !hasSecondPoint}
                    onClick={applyTwoPointCalibration}
                    style={{
                      ...buttonStyle,
                      background: "rgba(0,140,90,0.18)",
                      borderColor: "rgba(0,200,130,0.35)",
                      color: "#67d6a3",
                      cursor: isSaving || !hasSecondPoint ? "not-allowed" : "pointer",
                      opacity: isSaving || !hasSecondPoint ? 0.5 : 1
                    }}
                  >
                    Aplicar 2 pontos
                  </button>
                  <button
                    type="button"
                    disabled={isSaving}
                    onClick={() => battleMapStore.cancelTwoPointGridCalibration()}
                    style={{
                      ...buttonStyle,
                      background: "rgba(180,60,60,0.12)",
                      borderColor: "rgba(220,100,100,0.3)",
                      color: "#e49a9a",
                      cursor: isSaving ? "not-allowed" : "pointer"
                    }}
                  >
                    Cancelar 2 pontos
                  </button>
                </div>
              </>
            )}
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "rgba(20,30,46,0.75)",
              border: "1px solid rgba(55,82,116,0.6)",
              borderRadius: 6,
              padding: "8px 10px"
            }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", color: "#7892b6" }}>
                Tamanho das celulas
              </div>
              <div style={{ fontSize: 11, color: "#d8e6ff", lineHeight: 1.5 }}>
                Digite `X × Y` em pixels nativos do mapa. O grid recalcula `colunas × linhas`
                mantendo o retangulo atual.
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <input
                type="number"
                inputMode="decimal"
                min="1"
                step="0.5"
                disabled={isSaving || !canAdjustCellSize || uiState.isTwoPointCalibrationMode}
                value={cellWidthInput}
                onChange={(event) => {
                  const nextValue = event.currentTarget.value;
                  setCellInputs((currentInputs) => ({
                    ...currentInputs,
                    width: nextValue
                  }));
                  applyCellSize(nextValue, cellHeightInput);
                }}
                onBlur={() => {
                  if (canAdjustCellSize) {
                    setCellInputs((currentInputs) => ({
                      ...currentInputs,
                      width: currentCellWidthPx.toFixed(1)
                    }));
                  }
                }}
                style={{
                  ...numberInputStyle,
                  width: 84,
                  cursor: isSaving || !canAdjustCellSize || uiState.isTwoPointCalibrationMode ? "not-allowed" : "pointer",
                  opacity: isSaving || !canAdjustCellSize || uiState.isTwoPointCalibrationMode ? 0.5 : 1
                }}
              />

              <span style={{ color: "#89a6cb", fontSize: 13, fontWeight: 700 }}>×</span>

              <input
                type="number"
                inputMode="decimal"
                min="1"
                step="0.5"
                disabled={isSaving || !canAdjustCellSize || uiState.isTwoPointCalibrationMode}
                value={cellHeightInput}
                onChange={(event) => {
                  const nextValue = event.currentTarget.value;
                  setCellInputs((currentInputs) => ({
                    ...currentInputs,
                    height: nextValue
                  }));
                  applyCellSize(cellWidthInput, nextValue);
                }}
                onBlur={() => {
                  if (canAdjustCellSize) {
                    setCellInputs((currentInputs) => ({
                      ...currentInputs,
                      height: currentCellHeightPx.toFixed(1)
                    }));
                  }
                }}
                style={{
                  ...numberInputStyle,
                  width: 84,
                  cursor: isSaving || !canAdjustCellSize || uiState.isTwoPointCalibrationMode ? "not-allowed" : "pointer",
                  opacity: isSaving || !canAdjustCellSize || uiState.isTwoPointCalibrationMode ? 0.5 : 1
                }}
              />
            </div>
          </div>

          <div style={{ fontSize: 11, color: "#7d94b8", lineHeight: 1.7, fontFamily: "monospace" }}>
            x {draft.x.toFixed(3)} · y {draft.y.toFixed(3)}
            <br />
            w {draft.width.toFixed(3)} · h {draft.height.toFixed(3)}
            <br />
            cols {draftGridWidth} · rows {draftGridHeight}
          </div>

          <button
            type="button"
            disabled={isSaving}
            onClick={() =>
              submitGridCalibration(
                encounter.sessionId,
                draft,
                draftGridWidth,
                draftGridHeight
              )
            }
            style={{
              ...buttonStyle,
              background: isSaving ? "rgba(60,100,140,0.18)" : "rgba(0,140,90,0.18)",
              borderColor: isSaving ? "rgba(90,130,170,0.35)" : "rgba(0,200,130,0.35)",
              color: isSaving ? "#7e9cb8" : "#67d6a3",
              cursor: isSaving ? "wait" : "pointer"
            }}
          >
            {isSaving ? "Salvando..." : "Salvar alinhamento"}
          </button>

          <button
            type="button"
            disabled={isSaving}
            onClick={() => battleMapStore.cancelGridEdit()}
            style={{
              ...buttonStyle,
              background: "rgba(180,60,60,0.12)",
              borderColor: "rgba(220,100,100,0.3)",
              color: "#e49a9a",
              cursor: isSaving ? "not-allowed" : "pointer"
            }}
          >
            Cancelar
          </button>
        </>
      )}
    </section>
  );
}
