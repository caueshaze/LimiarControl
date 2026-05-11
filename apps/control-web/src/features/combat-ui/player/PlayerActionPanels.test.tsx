import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { PlayerActionPanels } from "./PlayerActionPanels";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    locale: "pt-BR",
    t: (key: string) =>
      ({
        "combatUi.weaponAttack": "Ataque com Arma",
        "combatUi.castSpell": "Conjurar magia",
        "combatUi.standardActions": "Ações padrão",
        "combatUi.useObject": "Usar Objeto",
        "combatUi.attack": "Atacar",
        "combatUi.noWeapon": "Nenhuma arma equipada",
        "combatUi.switchWeapon": "Trocar arma",
        "combatUi.switchWeaponPlaceholder": "Selecione uma arma...",
        "combatUi.switchWeaponHint": "Escolha a arma ativa para os próximos ataques.",
        "combatUi.meleeReachEffective": "Alcance corpo a corpo",
        "combatUi.meleeReachSizePrefix": "Tamanho",
        "playerBoard.creatureSize.Large": "Grande",
        "playerBoard.creatureSize.Huge": "Enorme",
      }[key] ?? key),
  }),
}));

vi.mock("../components/RangeStatusBadge", () => ({
  RangeStatusBadge: () => <div>range badge</div>,
}));

vi.mock("./PlayerUseObjectPanel", () => ({
  PlayerUseObjectPanel: () => <div>use object panel</div>,
}));

describe("PlayerActionPanels", () => {
  it("renderiza seletor de troca de arma no painel de ataque com a arma ativa destacada", () => {
    const markup = renderToStaticMarkup(
      <PlayerActionPanels
        activeActionPanel="attack"
        actionUsed={false}
        attackRangePreview={{
          loading: false,
          error: null,
          diagnostics: null,
          distanceMeters: null,
          normalRangeMeters: null,
          maxRangeMeters: null,
          effectiveReachMeters: null,
          rangeStatus: "unknown",
          hasDisadvantage: false,
          failureReasons: [],
        }}
        canAct
        consumableItemId=""
        consumableOptions={[]}
        dragonbornBreathWeaponAction={null}
        spiritualWeaponFollowUpAction={null}
        handleAttack={async () => undefined}
        handleCast={async () => undefined}
        handleDragonbornBreathWeapon={async () => undefined}
        onEnterSpiritualWeaponMode={() => undefined}
        handleStandardAction={async () => undefined}
        handleUseObject={async () => undefined}
        isSavingLoadout={false}
        loadoutStatus="Loadout atualizado."
        myParticipantId="participant-1"
        onWeaponChange={() => undefined}
        playerStatus={{
          currentWeapon: {
            attackBonus: 5,
            damageLabel: "1d8 cortante",
            name: "Espada longa",
            proficient: true,
            rangeMeters: 1.5,
            rangeLongMeters: null,
            isRanged: false,
          },
        } as any}
        selectedConsumable={null}
        selectedSpell={null}
        selectedSpellId=""
        selectedTarget={{ id: "target-1" }}
        selectedWeaponId="inv-sword"
        setActiveActionPanel={() => undefined}
        setConsumableItemId={() => undefined}
        setSelectedSpellId={() => undefined}
        setUseObjectManualRolls={() => undefined}
        setUseObjectNote={() => undefined}
        setUseObjectRollMode={() => undefined}
        setUseObjectTargetParticipantId={() => undefined}
        spellOptions={[]}
        spellRangePreview={{
          loading: false,
          error: null,
          diagnostics: null,
          distanceMeters: null,
          normalRangeMeters: null,
          maxRangeMeters: null,
          effectiveReachMeters: null,
          rangeStatus: "unknown",
          hasDisadvantage: false,
          failureReasons: [],
        }}
        targetId="target-1"
        turnResources={null}
        useObjectActionDisabled={false}
        useObjectManualRolls={[]}
        useObjectNote=""
        useObjectRollMode="system"
        useObjectTargetOptions={[]}
        useObjectTargetParticipantId=""
        weaponOptions={[
          { value: "inv-sword", label: "Espada longa", detail: "1d8 cortante · alcance 1.5m" },
          { value: "inv-bow", label: "Arco curto", detail: "1d6 perfurante · alcance 24m · longo 96m" },
        ]}
      />,
    );

    expect(markup).toContain("Espada longa");
    expect(markup).toContain("1d8 cortante · alcance 1.5m");
    expect(markup).toContain("Trocar arma");
    expect(markup).toContain("Arco curto · 1d6 perfurante · alcance 24m · longo 96m");
    expect(markup).toContain('option value="inv-sword" selected=""');
    expect(markup).toContain("Loadout atualizado.");
  });

  it("mostra alcance efetivo para atacante Large com arma melee", () => {
    const markup = renderToStaticMarkup(
      <PlayerActionPanels
        activeActionPanel="attack"
        actionUsed={false}
        attackRangePreview={{
          loading: false,
          error: null,
          diagnostics: null,
          distanceMeters: null,
          normalRangeMeters: 1.5,
          maxRangeMeters: null,
          effectiveReachMeters: 3,
          rangeStatus: "unknown",
          hasDisadvantage: false,
          failureReasons: [],
        }}
        canAct
        consumableItemId=""
        consumableOptions={[]}
        dragonbornBreathWeaponAction={null}
        spiritualWeaponFollowUpAction={null}
        handleAttack={async () => undefined}
        handleCast={async () => undefined}
        handleDragonbornBreathWeapon={async () => undefined}
        onEnterSpiritualWeaponMode={() => undefined}
        handleStandardAction={async () => undefined}
        handleUseObject={async () => undefined}
        isSavingLoadout={false}
        loadoutStatus={null}
        myParticipantId="participant-1"
        onWeaponChange={() => undefined}
        playerStatus={{
          currentWeapon: {
            attackBonus: 5,
            damageLabel: "1d8 cortante",
            name: "Espada longa",
            proficient: true,
            rangeMeters: 1.5,
            rangeLongMeters: null,
            isRanged: false,
          },
        } as any}
        selectedConsumable={null}
        selectedSpell={null}
        selectedSpellId=""
        selectedTarget={{ id: "target-1" }}
        selectedWeaponId="inv-sword"
        setActiveActionPanel={() => undefined}
        setConsumableItemId={() => undefined}
        setSelectedSpellId={() => undefined}
        setUseObjectManualRolls={() => undefined}
        setUseObjectNote={() => undefined}
        setUseObjectRollMode={() => undefined}
        setUseObjectTargetParticipantId={() => undefined}
        spellOptions={[]}
        spellRangePreview={{
          loading: false,
          error: null,
          diagnostics: null,
          distanceMeters: null,
          normalRangeMeters: null,
          maxRangeMeters: null,
          effectiveReachMeters: null,
          rangeStatus: "unknown",
          hasDisadvantage: false,
          failureReasons: [],
        }}
        targetId="target-1"
        turnResources={null}
        useObjectActionDisabled={false}
        useObjectManualRolls={[]}
        useObjectNote=""
        useObjectRollMode="system"
        useObjectTargetOptions={[]}
        useObjectTargetParticipantId=""
        weaponOptions={[]}
        effectiveSize="Large"
      />,
    );

    expect(markup).toContain("Alcance corpo a corpo: 3m");
    expect(markup).toContain("Tamanho Grande +1,5m");
  });

  it("nao mostra alcance efetivo para arma ranged mesmo com tamanho Large", () => {
    const markup = renderToStaticMarkup(
      <PlayerActionPanels
        activeActionPanel="attack"
        actionUsed={false}
        attackRangePreview={{
          loading: false,
          error: null,
          diagnostics: null,
          distanceMeters: null,
          normalRangeMeters: 24,
          maxRangeMeters: 96,
          effectiveReachMeters: null,
          rangeStatus: "unknown",
          hasDisadvantage: false,
          failureReasons: [],
        }}
        canAct
        consumableItemId=""
        consumableOptions={[]}
        dragonbornBreathWeaponAction={null}
        spiritualWeaponFollowUpAction={null}
        handleAttack={async () => undefined}
        handleCast={async () => undefined}
        handleDragonbornBreathWeapon={async () => undefined}
        onEnterSpiritualWeaponMode={() => undefined}
        handleStandardAction={async () => undefined}
        handleUseObject={async () => undefined}
        isSavingLoadout={false}
        loadoutStatus={null}
        myParticipantId="participant-1"
        onWeaponChange={() => undefined}
        playerStatus={{
          currentWeapon: {
            attackBonus: 3,
            damageLabel: "1d6 perfurante",
            name: "Arco curto",
            proficient: true,
            rangeMeters: 24,
            rangeLongMeters: 96,
            isRanged: true,
          },
        } as any}
        selectedConsumable={null}
        selectedSpell={null}
        selectedSpellId=""
        selectedTarget={{ id: "target-1" }}
        selectedWeaponId="inv-bow"
        setActiveActionPanel={() => undefined}
        setConsumableItemId={() => undefined}
        setSelectedSpellId={() => undefined}
        setUseObjectManualRolls={() => undefined}
        setUseObjectNote={() => undefined}
        setUseObjectRollMode={() => undefined}
        setUseObjectTargetParticipantId={() => undefined}
        spellOptions={[]}
        spellRangePreview={{
          loading: false,
          error: null,
          diagnostics: null,
          distanceMeters: null,
          normalRangeMeters: null,
          maxRangeMeters: null,
          effectiveReachMeters: null,
          rangeStatus: "unknown",
          hasDisadvantage: false,
          failureReasons: [],
        }}
        targetId="target-1"
        turnResources={null}
        useObjectActionDisabled={false}
        useObjectManualRolls={[]}
        useObjectNote=""
        useObjectRollMode="system"
        useObjectTargetOptions={[]}
        useObjectTargetParticipantId=""
        weaponOptions={[]}
        effectiveSize="Large"
      />,
    );

    expect(markup).not.toContain("Alcance corpo a corpo");
  });

  it("desabilita o seletor durante o salvamento", () => {
    const markup = renderToStaticMarkup(
      <PlayerActionPanels
        activeActionPanel="attack"
        actionUsed={false}
        attackRangePreview={{
          loading: false,
          error: null,
          diagnostics: null,
          distanceMeters: null,
          normalRangeMeters: null,
          maxRangeMeters: null,
          effectiveReachMeters: null,
          rangeStatus: "unknown",
          hasDisadvantage: false,
          failureReasons: [],
        }}
        canAct
        consumableItemId=""
        consumableOptions={[]}
        dragonbornBreathWeaponAction={null}
        spiritualWeaponFollowUpAction={null}
        handleAttack={async () => undefined}
        handleCast={async () => undefined}
        handleDragonbornBreathWeapon={async () => undefined}
        onEnterSpiritualWeaponMode={() => undefined}
        handleStandardAction={async () => undefined}
        handleUseObject={async () => undefined}
        isSavingLoadout
        loadoutStatus={null}
        myParticipantId="participant-1"
        onWeaponChange={() => undefined}
        playerStatus={null}
        selectedConsumable={null}
        selectedSpell={null}
        selectedSpellId=""
        selectedTarget={{ id: "target-1" }}
        selectedWeaponId=""
        setActiveActionPanel={() => undefined}
        setConsumableItemId={() => undefined}
        setSelectedSpellId={() => undefined}
        setUseObjectManualRolls={() => undefined}
        setUseObjectNote={() => undefined}
        setUseObjectRollMode={() => undefined}
        setUseObjectTargetParticipantId={() => undefined}
        spellOptions={[]}
        spellRangePreview={{
          loading: false,
          error: null,
          diagnostics: null,
          distanceMeters: null,
          normalRangeMeters: null,
          maxRangeMeters: null,
          effectiveReachMeters: null,
          rangeStatus: "unknown",
          hasDisadvantage: false,
          failureReasons: [],
        }}
        targetId="target-1"
        turnResources={null}
        useObjectActionDisabled={false}
        useObjectManualRolls={[]}
        useObjectNote=""
        useObjectRollMode="system"
        useObjectTargetOptions={[]}
        useObjectTargetParticipantId=""
        weaponOptions={[{ value: "inv-sword", label: "Espada longa", detail: "1d8 cortante · alcance 1.5m" }]}
      />,
    );

    expect(markup).toContain("<select");
    expect(markup).toContain("disabled=\"\"");
  });
});
