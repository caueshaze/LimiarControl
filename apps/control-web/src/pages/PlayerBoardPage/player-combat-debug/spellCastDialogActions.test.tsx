import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { SpellCastDialogActions } from "./SpellCastDialogActions";

describe("SpellCastDialogActions", () => {
  const baseProps = {
    attackMode: "choose" as const,
    canSubmitArea: true,
    isAreaSpell: false,
    loading: false,
    onAttackModeChange: vi.fn(),
    onCancel: vi.fn(),
    onClearArea: vi.fn(),
    onShowAreaHint: false,
    onSubmitCast: vi.fn(),
    spellMode: "spell_attack",
    spellOutOfRange: false,
    submitDisabled: false,
    validationMessage: null,
  };

  it("renderiza botao de Cancelar no modo spell_attack (choose)", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogActions {...baseProps} attackMode="choose" />
    );
    expect(markup).toContain("Cancelar");
    expect(markup).toContain("Virtual");
    expect(markup).toContain("Manual");
  });

  it("renderiza botao de Cancelar no modo spell_attack (virtual)", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogActions {...baseProps} attackMode="virtual" />
    );
    expect(markup).toContain("Cancelar");
    expect(markup).toContain("Rolar ataque magico");
  });

  it("renderiza botao de Cancelar no modo spell_attack (manual)", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogActions {...baseProps} attackMode="manual" />
    );
    expect(markup).toContain("Cancelar");
  });

  it("renderiza botao de Cancelar para saving_throw", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogActions {...baseProps} spellMode="saving_throw" />
    );
    expect(markup).toContain("Cancelar");
    expect(markup).toContain("Conjurar");
  });
  it("esconde botões principais quando tem erro", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogActions {...baseProps} attackMode="choose" hasError={true} />
    );
    expect(markup).toContain("Cancelar");
    expect(markup).not.toContain("Virtual");
    expect(markup).not.toContain("Manual");
  });
});
