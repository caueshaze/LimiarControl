import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { LoadSummaryCard, StatCard, WeaponCard } from "./PlayerBoardStatusCards";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) =>
      ({
        "playerBoard.equippedWeaponLabel": "Arma equipada",
        "playerBoard.noCurrentWeapon": "Sem arma",
        "playerBoard.noCurrentWeaponHint": "Equipe uma arma para ver os detalhes.",
        "playerBoard.weaponProficient": "Proficiente",
        "playerBoard.weaponNotProficient": "Sem proficiência",
        "playerBoard.weaponToHitSuffix": "para acertar",
        "playerBoard.combatOpenState": "Combate ativo",
        "playerBoard.rollRequest": "Teste pendente",
        "playerBoard.encumbranceTierLabel": "Carga",
        "playerBoard.encumbranceCurrentShortLabel": "Atual",
        "playerBoard.carryingCapacityShortLabel": "Carga máx.",
        "playerBoard.carryingCapacityLabel": "Capacidade de carga",
        "playerBoard.carryingCapacityBase": "Base",
        "playerBoard.pushDragLiftShortLabel": "Empurrar",
        "playerBoard.pushDragLiftLabel": "Empurrar/Puxar/Levantar",
        "playerBoard.creatureSize.Tiny": "Diminuto",
        "playerBoard.creatureSize.Small": "Pequeno",
        "playerBoard.creatureSize.Medium": "Médio",
        "playerBoard.creatureSize.Large": "Grande",
        "playerBoard.creatureSize.Huge": "Enorme",
        "playerBoard.creatureSize.Gargantuan": "Colossal",
      }[key] ?? key),
  }),
}));

describe("PlayerBoardStatusCards", () => {
  it("permite quebra de texto em StatCard para labels longos", () => {
    const markup = renderToStaticMarkup(
      <StatCard
        label="Empurrar/Puxar/Levantar"
        value="231 kg"
        helper="Texto auxiliar muito longo para validar a quebra."
      />,
    );

    expect(markup).toContain("min-w-0");
    expect(markup).toContain("break-words");
    expect(markup).toContain("leading-4");
  });

  it("mantém WeaponCard flexível para nomes e dano longos", () => {
    const markup = renderToStaticMarkup(
      <WeaponCard
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          currentWeapon: {
            name: "Ataque desarmado extremamente verboso",
            proficient: true,
            attackBonus: 5,
            damageLabel: "1 + 3 Contundente com uma descrição maior que o normal",
          },
        } as any}
      />,
    );

    expect(markup).toContain("min-w-0");
    expect(markup).toContain("Ataque desarmado extremamente verboso");
    expect(markup).toContain("break-words");
  });

  it("consolida métricas de carga em um card largo com labels curtos no mobile", () => {
    const markup = renderToStaticMarkup(
      <LoadSummaryCard
        baseCarryingCapacityKg={58}
        carryingCapacityKg={116}
        carryingCapacitySources={[{ label: "Bear", multiplier: 2 }]}
        encumbranceAccent="text-slate-300"
        encumbranceTierLabel="27 kg"
        encumbranceHelper={null}
        pushDragLiftKg={231}
      />,
    );

    expect(markup).toContain("Capacidade de carga");
    expect(markup).toContain("Carga máx.");
    expect(markup).toContain("Empurrar/Puxar/Levantar");
    expect(markup).toContain("231 kg");
  });

  it("localiza fonte de tamanho usando i18n", () => {
    const markup = renderToStaticMarkup(
      <LoadSummaryCard
        baseCarryingCapacityKg={68}
        carryingCapacityKg={136}
        carryingCapacitySources={[{ label: "Large", multiplier: 2, groupKey: "__size_multiplier" }]}
        encumbranceAccent="text-slate-300"
        encumbranceTierLabel="Normal"
        encumbranceHelper={null}
        pushDragLiftKg={272}
      />,
    );

    expect(markup).toContain("Grande ×2");
    expect(markup).not.toContain("Large ×2");
  });
});
