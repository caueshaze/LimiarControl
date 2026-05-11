import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { PlayerBoardStatusPanel } from "./PlayerBoardStatusPanel";

type CastCardProps = {
  casting: boolean;
  onCast: (...args: unknown[]) => unknown;
  spells: unknown[];
  targetOptions?: { playerUserId: string; label: string }[];
};

const requireCastCardProps = (value: CastCardProps | null): CastCardProps => {
  if (!value) {
    throw new Error("Expected cast card props to be captured");
  }
  return value;
};

vi.mock("../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) =>
      ({
        "playerBoard.statusPanelTitle": "Base de combate",
        "playerBoard.statusPanelHeading": "Resumo do aventureiro",
        "playerBoard.statusPanelDescription": "Descricao",
        "playerBoard.waitingSheetState": "Aguardando ficha",
        "sheet.basicInfo.level": "Nível",
        "playerBoard.currentHpLabel": "Vida atual",
        "playerBoard.tempHpLabel": "Temp HP",
        "playerBoard.xpProgressLabel": "XP",
        "sheet.progress.maxLevel": "Max",
        "playerBoard.armorClassLabel": "CA",
        "playerBoard.hpTrackLabel": "HP",
        "playerBoard.xpTrackLabel": "Progresso",
        "playerBoard.initiativeLabel": "Iniciativa",
        "sheet.skills.passivePerception": "Percepção passiva",
        "playerBoard.spellResourcesTitle": "Slots de magia",
        "playerBoard.noSpellSlots": "Sem slots de magia ativos.",
        "playerBoard.activeConcentrationLabel": "Concentração",
        "playerBoard.clearConcentration": "Encerrar concentração",
        "playerBoard.clearingConcentration": "Encerrando...",
        "playerBoard.activeEffectsLabel": "Efeitos ativos",
        "playerBoard.activeEffectFallback": "Efeito",
        "playerBoard.removeEffect": "Remover",
        "playerBoard.removingEffect": "Removendo...",
        "playerBoard.lifecycleConcentration": "Concentração",
        "playerBoard.lifecycleManual": "Manual",
        "playerBoard.lifecycleRounds": "{count} rodadas",
        "playerBoard.lifecycleRoundsUnknown": "Por rodadas",
        "playerBoard.lifecycleUntilTurnStart": "Até início do turno",
        "playerBoard.lifecycleUntilTurnEnd": "Até fim do turno",
        "playerBoard.lifecycleUntilLongRest": "Até descanso longo",
        "playerBoard.lifecycleUntilShortRest": "Até descanso curto",
        "playerBoard.lifecycleUntilRemoved": "Até remover",
        "playerBoard.lifecycleLongRest": "Limpa no descanso longo",
        "playerBoard.speedLabel": "Deslocamento",
        "playerBoard.speedPenaltyHint": "Penalidade de carga",
        "playerBoard.creatureSizeLabel": "Tamanho",
        "playerBoard.creatureSize.Tiny": "Diminuto",
        "playerBoard.creatureSize.Small": "Pequeno",
        "playerBoard.creatureSize.Medium": "Médio",
        "playerBoard.creatureSize.Large": "Grande",
        "playerBoard.creatureSize.Huge": "Enorme",
        "playerBoard.creatureSize.Gargantuan": "Colossal",
        "playerBoard.carryingCapacityLabel": "Capacidade",
        "playerBoard.pushDragLiftLabel": "Empurrar",
        "playerBoard.encumbranceTierLabel": "Peso",
      }[key] ?? key),
  }),
}));

let lastCastCardProps: CastCardProps | null = null;

vi.mock("./OutOfCombatSpellCastCard", () => ({
  OutOfCombatSpellCastCard: (props: CastCardProps) => {
    lastCastCardProps = props;
    return props.spells.length > 0 ? <div data-testid="cast-card">cast-card</div> : null;
  },
}));

vi.mock("./player-board-status/PlayerBoardStatusCards", () => ({
  DeathSaveCard: () => <div>death</div>,
  LoadSummaryCard: () => <div>load-summary</div>,
  ProgressCard: ({ label, value }: { label: string; value: string }) => <div>{label}:{value}</div>,
  RestCard: () => <div>rest</div>,
  StatCard: ({ label, value, helper }: { label: string; value: string; helper?: string | null }) => (
    <div>{label}:{value}{helper ? <span>{helper}</span> : null}</div>
  ),
  WeaponCard: () => <div>weapon</div>,
  getHpBarToneClass: () => "hp-bar",
  getHpToneClass: () => "hp-tone",
}));

describe("PlayerBoardStatusPanel", () => {
  it("mostra resumo persistente de slots de magia quando a ficha tem spellcasting", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        combatActive
        pendingRoll={null}
        playerSheet={{
          spellcasting: {
            ability: "intelligence",
            mode: "known",
            slots: {
              1: { max: 4, used: 2 },
              2: { max: 3, used: 3 },
            },
            spells: [],
          },
        } as any}
        playerStatus={{
          level: 5,
          currentHp: 18,
          maxHp: 24,
          hpPercent: 75,
          tempHp: 0,
          xpPercent: 40,
          nextLevelThreshold: 1000,
          experiencePoints: 400,
          ac: 15,
          initiative: 2,
          passivePerception: 14,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Slots de magia");
    expect(markup).toContain("1º círculo");
    expect(markup).toContain("2/4 restantes");
    expect(markup).toContain("2º círculo");
    expect(markup).toContain("0/3 restantes");
  });

  it("mostra percepção passiva sem breakdown quando sem bônus", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Percepção passiva:13");
    expect(markup).not.toContain("Owl");
  });

  it("mostra breakdown de percepção passiva quando passivePerceptionBonus está presente", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        combatActive
        pendingRoll={null}
        playerStatus={{
          level: 4,
          currentHp: 22,
          maxHp: 30,
          hpPercent: 73,
          tempHp: 0,
          xpPercent: 60,
          nextLevelThreshold: 2700,
          experiencePoints: 1800,
          ac: 14,
          initiative: 2,
          passivePerception: 17,
          passivePerceptionBonus: 5,
          passivePerceptionBonusSources: [{ label: "Owl's Wisdom", value: 5 }],
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Percepção passiva:17");
    expect(markup).toContain("Base 12 + Owl&#x27;s Wisdom +5");
  });

  it("renderiza label de concentração ativa quando activeConcentration existe", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeConcentration={{
          spellName: "Bless",
          variantLabel: "Ally",
          effectIds: ["eff-1"],
        }}
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Concentração");
    expect(markup).toContain("Bless — Ally");
    expect(markup).toContain("Encerrar concentração");
  });

  it("prefere spellName + variantLabel no label de concentração", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeConcentration={{
          spellName: "Bless",
          variantLabel: "Ally",
          spellKey: "bless",
          effectIds: ["eff-1"],
        }}
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Bless — Ally");
  });

  it("fallback para spellName sozinho quando variantLabel está ausente", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeConcentration={{
          spellName: "Bless",
          effectIds: ["eff-1"],
        }}
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Bless");
    expect(markup).not.toContain("—");
  });

  it("fallback para spellKey quando ambos os nomes estão ausentes", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeConcentration={{
          spellKey: "bless",
          effectIds: ["eff-1"],
        }}
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("bless");
  });

  it("desabilita botão de encerrar concentração quando clearingConcentration é true", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeConcentration={{
          spellName: "Bless",
          effectIds: ["eff-1"],
        }}
        clearingConcentration
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("disabled");
    expect(markup).toContain("Encerrando...");
  });

  it("mostra tamanho efetivo traduzido quando difere do tamanho base", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        combatActive={false}
        participant={{ base_size: "medium", effective_size: "large" } as any}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Tamanho");
    expect(markup).toContain("Grande (base Médio)");
  });

  it("não renderiza card de concentração quando activeConcentration é nulo", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeConcentration={null}
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).not.toContain("Concentração");
    expect(markup).not.toContain("Encerrar concentração");
  });

  it("atualiza percepção passiva após remoção de bônus (simula clear de concentração)", () => {
    const baseStatus = {
      level: 4,
      currentHp: 22,
      maxHp: 30,
      hpPercent: 73,
      tempHp: 0,
      xpPercent: 60,
      nextLevelThreshold: 2700,
      experiencePoints: 1800,
      ac: 14,
      initiative: 2,
    };

    const withBonus = {
      ...baseStatus,
      passivePerception: 17,
      passivePerceptionBonus: 5,
      passivePerceptionBonusSources: [{ label: "Owl's Wisdom", value: 5 }],
    };

    const withoutBonus = {
      ...baseStatus,
      passivePerception: 12,
      passivePerceptionBonus: 0,
      passivePerceptionBonusSources: [],
    };

    const markupWith = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeConcentration={{
          spellName: "Owl's Wisdom",
          effectIds: ["eff-1"],
        }}
        combatActive={false}
        pendingRoll={null}
        playerStatus={withBonus as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markupWith).toContain("Percepção passiva:17");
    expect(markupWith).toContain("Base 12 + Owl&#x27;s Wisdom +5");

    const markupWithout = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeConcentration={null}
        combatActive={false}
        pendingRoll={null}
        playerStatus={withoutBonus as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markupWithout).toContain("Percepção passiva:12");
    expect(markupWithout).not.toContain("Owl");
  });

  it("renderiza painel de efeitos ativos quando activeSpellEffects existem", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeSpellEffects={[
          {
            id: "eff-1",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-01-01T00:00:00Z",
            display_label: "Owl's Wisdom",
            metadata: {
              source_spell_name: "Owl's Wisdom",
              concentration: true,
              concentration_group: "grp-1",
            },
          },
          {
            id: "eff-2",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-01-01T00:00:00Z",
            metadata: {
              source_spell_name: "Shield of Faith",
            },
          },
        ] as any}
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Efeitos ativos");
    expect(markup).toContain("Owl&#x27;s Wisdom");
    expect(markup).toContain("Concentração");
    expect(markup).toContain("Shield of Faith");
    expect(markup).toContain("Remover");
    // Lifecycle badges for concentration manual effect
    expect(markup).toContain("Manual");
    expect(markup).toContain("Limpa no descanso longo");
  });

  it("renderiza badges de ciclo de vida para efeito manual sem concentração", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeSpellEffects={[
          {
            id: "eff-1",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-01-01T00:00:00Z",
            display_label: "Cat's Grace",
            metadata: { source_spell_name: "Cat's Grace" },
          },
        ] as any}
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Cat&#x27;s Grace");
    expect(markup).toContain("Manual");
    expect(markup).toContain("Limpa no descanso longo");
    expect(markup).not.toContain("Concentração");
  });

  it("renderiza badge de rodadas para efeito com duration_type rounds", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeSpellEffects={[
          {
            id: "eff-1",
            kind: "spell_effect",
            duration_type: "rounds",
            remaining_rounds: 5,
            created_at: "2026-01-01T00:00:00Z",
            display_label: "Haste",
            metadata: {},
          },
        ] as any}
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Haste");
    expect(markup).toContain("5 rodadas");
  });

  it("não renderiza painel de efeitos ativos quando a lista está vazia", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeSpellEffects={[]}
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).not.toContain("Efeitos ativos");
  });

  it("desabilita botão de remover quando removingEffectId corresponde", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        activeSpellEffects={[
          {
            id: "eff-1",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-01-01T00:00:00Z",
            display_label: "Bless",
            metadata: {},
          },
        ] as any}
        removingEffectId="eff-1"
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          level: 3,
          currentHp: 20,
          maxHp: 20,
          hpPercent: 100,
          tempHp: 0,
          xpPercent: 10,
          nextLevelThreshold: 900,
          experiencePoints: 100,
          ac: 12,
          initiative: 1,
          passivePerception: 13,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("disabled");
    expect(markup).toContain("Removendo...");
  });
});

describe("PlayerBoardStatusPanel – out-of-combat spell casting", () => {
  const baseProps = {
    combatActive: false,
    pendingRoll: null,
    playerStatus: {
      level: 3,
      currentHp: 20,
      maxHp: 20,
      hpPercent: 100,
      tempHp: 0,
      xpPercent: 10,
      nextLevelThreshold: 900,
      experiencePoints: 100,
      ac: 12,
      initiative: 1,
      passivePerception: 13,
    } as any,
    restState: "exploration" as const,
    usingHitDie: false,
    onUseHitDie: () => undefined,
    onClearConcentration: () => undefined,
    onRemoveEffect: () => undefined,
  };

  const eligibleSpell = {
    id: "spell-sof-1",
    canonicalKey: "shield_of_faith",
    nameEn: "Shield of Faith",
    namePt: "Escudo da Fé",
    level: 1,
    concentration: true,
    prepared: true,
    variants: [],
    effects: [],
  } as any;

  it("renders cast card when not in combat and spells are available", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        {...baseProps}
        castableSpells={[eligibleSpell]}
        onCastSpell={() => undefined}
      />,
    );
    expect(markup).toContain("cast-card");
  });

  it("hides cast card when combat is active", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        {...baseProps}
        combatActive={true}
        castableSpells={[eligibleSpell]}
        onCastSpell={() => undefined}
      />,
    );
    expect(markup).not.toContain("cast-card");
  });

  it("hides cast card when castableSpells is empty", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        {...baseProps}
        castableSpells={[]}
        onCastSpell={() => undefined}
      />,
    );
    expect(markup).not.toContain("cast-card");
  });

  it("hides cast card when onCastSpell is not provided", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        {...baseProps}
        castableSpells={[eligibleSpell]}
      />,
    );
    expect(markup).not.toContain("cast-card");
  });

  it("passes targetOptions to OutOfCombatSpellCastCard", () => {
    const targetOptions = [{ playerUserId: "u1", label: "Player 1" }];
    lastCastCardProps = null;
    renderToStaticMarkup(
      <PlayerBoardStatusPanel
        {...baseProps}
        castableSpells={[eligibleSpell]}
        onCastSpell={() => undefined}
        targetOptions={targetOptions}
      />,
    );
    expect(requireCastCardProps(lastCastCardProps).targetOptions).toEqual(targetOptions);
  });

  it("passes castingSpell as casting to OutOfCombatSpellCastCard", () => {
    lastCastCardProps = null;
    renderToStaticMarkup(
      <PlayerBoardStatusPanel
        {...baseProps}
        castableSpells={[eligibleSpell]}
        onCastSpell={() => undefined}
        castingSpell={true}
      />,
    );
    expect(requireCastCardProps(lastCastCardProps).casting).toBe(true);
  });

  it("passes onCastSpell as onCast to OutOfCombatSpellCastCard", () => {
    const handleCast = () => undefined;
    lastCastCardProps = null;
    renderToStaticMarkup(
      <PlayerBoardStatusPanel
        {...baseProps}
        castableSpells={[eligibleSpell]}
        onCastSpell={handleCast}
      />,
    );
    expect(requireCastCardProps(lastCastCardProps).onCast).toBe(handleCast);
  });
});

describe("PlayerBoardStatusPanel – movement speed", () => {
  const baseStatus = {
    level: 3,
    currentHp: 20,
    maxHp: 20,
    hpPercent: 100,
    tempHp: 0,
    xpPercent: 10,
    nextLevelThreshold: 900,
    experiencePoints: 100,
    ac: 12,
    initiative: 1,
    passivePerception: 13,
    baseSpeedMeters: 9,
    effectiveSpeedMeters: 9,
    encumbranceTier: "normal" as const,
    encumbranceNormalMaxKg: 22,
    encumbranceEncumberedMaxKg: 45,
    encumbranceHeavilyEncumberedMaxKg: 68,
    totalWeightKg: 10,
    baseCarryingCapacityKg: 68,
    carryingCapacityKg: 68,
    pushDragLiftKg: 136,
    hitDiceRemaining: 3,
    hitDiceTotal: 3,
    hitDieType: "d8",
  };

  it("shows base speed when no bonus", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        combatActive={false}
        pendingRoll={null}
        playerStatus={{ ...baseStatus } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );
    expect(markup).toContain("9 m");
    expect(markup).not.toContain("Passos Longos");
    expect(markup).not.toContain("Penalidade de carga");
  });

  it("shows boosted speed with bonus helper", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          ...baseStatus,
          effectiveSpeedMeters: 12,
          movementSpeedBonus: 3,
          movementSpeedBonusSources: [{ label: "Passos Longos", value: 3 }],
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );
    expect(markup).toContain("12 m");
    expect(markup).toContain("Passos Longos");
    expect(markup).toContain("base 9 m");
  });

  it("shows encumbrance penalty and bonus together", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          ...baseStatus,
          effectiveSpeedMeters: 7,
          baseSpeedMeters: 9,
          encumbranceTier: "encumbered",
          movementSpeedBonus: 1,
          movementSpeedBonusSources: [{ label: "Passos Longos", value: 1 }],
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );
    expect(markup).toContain("9 m");
    expect(markup).toContain("Penalidade de carga");
    expect(markup).toContain("Passos Longos");
  });

  it("does not crash with malformed movementSpeedBonusSources", () => {
    const markup = renderToStaticMarkup(
      <PlayerBoardStatusPanel
        combatActive={false}
        pendingRoll={null}
        playerStatus={{
          ...baseStatus,
          movementSpeedBonus: null,
          movementSpeedBonusSources: null,
        } as any}
        restState="exploration"
        usingHitDie={false}
        onUseHitDie={() => undefined}
        onClearConcentration={() => undefined}
        onRemoveEffect={() => undefined}
      />,
    );
    expect(markup).toContain("9 m");
  });
});
