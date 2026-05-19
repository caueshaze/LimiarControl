import { describe, expect, it } from "vitest";
import { resolveBootstrapPresentation } from "./CombatMapFrame";

describe("resolveBootstrapPresentation", () => {
  it("treats combat_not_active as a calm waiting state", () => {
    expect(resolveBootstrapPresentation("combat_not_active")).toEqual({
      message: "Aguardando o combate comecar para abrir o mapa tatico.",
      tone: "info",
      canRetry: false,
    });
  });

  it("treats combat_not_found as a calm waiting state", () => {
    expect(resolveBootstrapPresentation("combat_not_found")).toEqual({
      message: "Aguardando o inicio do combate para abrir o mapa tatico.",
      tone: "info",
      canRetry: false,
    });
  });

  it("keeps real bootstrap failures retryable", () => {
    expect(resolveBootstrapPresentation("no_combatants")).toEqual({
      message: "Nao foi possivel sincronizar o mapa porque o combate nao possui participantes validos.",
      tone: "error",
      canRetry: true,
    });
  });
});
