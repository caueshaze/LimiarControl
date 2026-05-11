import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { RangeStatusBadge } from "./RangeStatusBadge";
import type { TargetingPreviewState } from "../hooks/useTargetingPreview";

const basePreview: TargetingPreviewState = {
  loading: false,
  error: null,
  diagnostics: null,
  distanceMeters: 3,
  normalRangeMeters: 1.5,
  maxRangeMeters: null,
  effectiveReachMeters: null,
  rangeStatus: "normal",
  hasDisadvantage: false,
  failureReasons: [],
};

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    locale: "pt",
    t: (key: string) =>
      ({
        "combatUi.rangeNormal": "No alcance",
        "combatUi.rangeLong": "Alcance longo",
        "combatUi.rangeOut": "Fora de alcance",
        "combatUi.rangeUnknown": "Alcance desconhecido",
        "combatUi.rangeChecking": "Checando alcance...",
        "combatUi.disadvantageRange": "Desvantagem por alcance longo",
        "combatUi.meleeReachEffective": "Alcance corpo a corpo",
        "combatUi.meleeReachBase": "Base",
        "combatUi.meleeReachSizePrefix": "Tamanho",
        "playerBoard.creatureSize.Large": "Grande",
        "playerBoard.creatureSize.Huge": "Enorme",
        "playerBoard.creatureSize.Gargantuan": "Colossal",
      }[key] ?? key),
  }),
}));

describe("RangeStatusBadge", () => {
  it("renders normal range without size bonus", () => {
    const markup = renderToStaticMarkup(<RangeStatusBadge preview={basePreview} />);
    expect(markup).toContain("No alcance");
    expect(markup).toContain("Alcance normal: 1,5m");
  });

  it("shows effective reach breakdown for Large attacker", () => {
    const preview: TargetingPreviewState = {
      ...basePreview,
      effectiveReachMeters: 3,
    };
    const markup = renderToStaticMarkup(<RangeStatusBadge preview={preview} effectiveSize="Large" />);
    expect(markup).toContain("Alcance corpo a corpo: 3m");
    expect(markup).toContain("Base: 1,5m");
    expect(markup).toContain("Tamanho Grande +1,5m");
  });

  it("shows only source when no normalRangeLabel exists", () => {
    const preview: TargetingPreviewState = {
      ...basePreview,
      normalRangeMeters: null,
      effectiveReachMeters: 3,
    };
    const markup = renderToStaticMarkup(<RangeStatusBadge preview={preview} effectiveSize="Large" />);
    expect(markup).toContain("Alcance corpo a corpo: 3m");
    expect(markup).toContain("Tamanho Grande +1,5m");
  });

  it("does not show breakdown when effectiveSize is Medium", () => {
    const preview: TargetingPreviewState = {
      ...basePreview,
      effectiveReachMeters: 1.5,
    };
    const markup = renderToStaticMarkup(<RangeStatusBadge preview={preview} effectiveSize="Medium" />);
    expect(markup).not.toContain("Alcance corpo a corpo");
    expect(markup).toContain("Alcance normal: 1,5m");
  });

  it("does not show breakdown when effectiveSize is missing", () => {
    const preview: TargetingPreviewState = {
      ...basePreview,
      effectiveReachMeters: 3,
    };
    const markup = renderToStaticMarkup(<RangeStatusBadge preview={preview} />);
    expect(markup).not.toContain("Alcance corpo a corpo");
  });

  it("uses effectiveReachMeters as needed label for out-of-range", () => {
    const preview: TargetingPreviewState = {
      ...basePreview,
      rangeStatus: "out",
      distanceMeters: 4.5,
      effectiveReachMeters: 3,
    };
    const markup = renderToStaticMarkup(<RangeStatusBadge preview={preview} effectiveSize="Large" />);
    expect(markup).toContain("precisa &lt;= 3m");
  });
});
