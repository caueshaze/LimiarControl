import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { PlayerBoardStatusPanel } from "./PlayerBoardStatusPanel";

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
      }[key] ?? key),
  }),
}));

vi.mock("./player-board-status/PlayerBoardStatusCards", () => ({
  DeathSaveCard: () => <div>death</div>,
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
      />,
    );

    expect(markup).toContain("Percepção passiva:17");
    expect(markup).toContain("Base 12 + Owl&#x27;s Wisdom +5");
  });
});
