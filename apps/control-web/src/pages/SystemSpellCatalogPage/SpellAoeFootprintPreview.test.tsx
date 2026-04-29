import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SpellAoeFootprintPreview } from "./SpellAoeFootprintPreview";

const defaultProps = {
  areaShape: "",
  radiusMeters: "",
  lengthMeters: "",
  sideMeters: "",
};

describe("SpellAoeFootprintPreview", () => {
  it("shows empty state when no areaShape is set", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview {...defaultProps} />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview-empty\"");
    expect(markup).not.toContain("data-testid=\"spell-aoe-preview\"");
    expect(markup).not.toContain("data-testid=\"spell-aoe-preview-warning\"");
  });

  it("shows warning for sphere without radiusMeters", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview {...defaultProps} areaShape="sphere" />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview-warning\"");
    expect(markup).toContain("raio");
  });

  it("shows warning for cone without lengthMeters", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview {...defaultProps} areaShape="cone" />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview-warning\"");
    expect(markup).toContain("comprimento");
  });

  it("shows warning for cube without sideMeters", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview {...defaultProps} areaShape="cube" />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview-warning\"");
    expect(markup).toContain("tamanho do lado");
  });

  it("shows warning for line without lengthMeters", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview {...defaultProps} areaShape="line" />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview-warning\"");
  });

  it("renders grid for sphere with valid radiusMeters", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview
        {...defaultProps}
        areaShape="sphere"
        radiusMeters="6"
      />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview\"");
    expect(markup).toContain("célula");
    expect(markup).not.toContain("data-testid=\"spell-aoe-preview-warning\"");
  });

  it("renders grid for cylinder with valid radiusMeters", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview
        {...defaultProps}
        areaShape="cylinder"
        radiusMeters="3"
      />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview\"");
  });

  it("renders grid for cone with valid lengthMeters", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview
        {...defaultProps}
        areaShape="cone"
        lengthMeters="9"
      />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview\"");
  });

  it("renders grid for line with valid lengthMeters", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview
        {...defaultProps}
        areaShape="line"
        lengthMeters="9"
      />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview\"");
  });

  it("renders grid for cube with valid sideMeters", () => {
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview
        {...defaultProps}
        areaShape="cube"
        sideMeters="6"
      />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview\"");
  });

  it("uses radiusMeters for sphere, not lengthMeters or sideMeters", () => {
    // sphere with radiusMeters filled but lengthMeters missing → should show grid
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview
        {...defaultProps}
        areaShape="sphere"
        radiusMeters="4.5"
        lengthMeters=""
        sideMeters=""
      />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview\"");
  });

  it("uses sideMeters for cube, not radiusMeters", () => {
    // cube with sideMeters filled but radiusMeters missing → should show grid
    const markup = renderToStaticMarkup(
      <SpellAoeFootprintPreview
        {...defaultProps}
        areaShape="cube"
        radiusMeters=""
        sideMeters="4.5"
      />,
    );
    expect(markup).toContain("data-testid=\"spell-aoe-preview\"");
  });
});
