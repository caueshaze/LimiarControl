import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  PlayerSpellCastDialog,
  buildNonAreaSpellCastPayload,
  getEffectiveEffectInstanceContext,
} from "./PlayerSpellCastDialog";
import { reconcileEffectInstanceTargets, resolveEffectInstanceContext } from "./InstanceTargetSelector";

let lastActionsProps: Record<string, unknown> | null = null;
let resolvedSpellContextState = {
  context: null as Record<string, unknown> | null,
  error: null as string | null,
  loading: false,
};

vi.mock("../../../shared/api/combatRepo", () => ({
  combatRepo: {
    castSpell: vi.fn(),
    castSpellEffect: vi.fn(),
  },
}));

vi.mock("../../../features/combat-ui/hooks/useTargetingPreview", () => ({
  useTargetingPreview: () => ({
    loading: false,
    error: null,
    diagnostics: null,
    distanceMeters: null,
    normalRangeMeters: null,
    maxRangeMeters: null,
    rangeStatus: "unknown",
    hasDisadvantage: false,
    failureReasons: [],
  }),
}));

vi.mock("./useAreaTargeting", () => ({
  useAreaTargeting: () => ({
    anchorCell: null,
    canSubmitArea: false,
    clearAreaSelection: vi.fn(),
    isAreaSpell: false,
    mapError: null,
    mapLoading: false,
    mapState: null,
    originCell: null,
    preview: null,
    previewError: null,
    previewLoading: false,
    setAnchorCell: vi.fn(),
  }),
}));

vi.mock("./useResolvedSpellContext", () => ({
  useResolvedSpellContext: () => resolvedSpellContextState,
}));

vi.mock("./SpellCastDialogHeader", () => ({
  SpellCastDialogHeader: () => <div>header</div>,
}));

vi.mock("./SpellCastDialogActions", () => ({
  SpellCastDialogActions: (props: Record<string, unknown>) => {
    lastActionsProps = props;
    return <div>actions</div>;
  },
}));

vi.mock("./SpellCastResultPanel", () => ({
  SpellCastResultPanel: () => <div>result</div>,
}));

vi.mock("./AreaTargetingGrid", () => ({
  AreaTargetingGrid: () => <div>area</div>,
}));

const actor = {
  id: "player-1",
  kind: "player" as const,
  ref_id: "player:1",
  display_name: "Mage",
  initiative: 15,
  status: "active" as const,
  team: "players" as const,
  visible: true,
  actor_user_id: "user-1",
};

const target = {
  id: "enemy-1",
  kind: "session_entity" as const,
  ref_id: "session_entity:goblin-a",
  display_name: "Goblin A",
  initiative: 10,
  status: "active" as const,
  team: "enemies" as const,
  visible: true,
  actor_user_id: null,
};

const participants = [
  actor,
  target,
  {
    id: "enemy-2",
    kind: "session_entity" as const,
    ref_id: "session_entity:goblin-b",
    display_name: "Goblin B",
    initiative: 8,
    status: "active" as const,
    team: "enemies" as const,
    visible: true,
    actor_user_id: null,
  },
];

const baseProps = {
  actor,
  actorParticipantId: actor.id,
  onClose: () => undefined,
  onResolved: () => undefined,
  participants,
  sessionId: "session-1",
  spellDamageType: "Force",
  spellEffectBonus: "0",
  spellEffectDice: "1d10",
  spellMode: "spell_attack" as const,
  spellSaveAbility: "",
  target,
};

describe("PlayerSpellCastDialog", () => {
  beforeEach(() => {
    lastActionsProps = null;
    resolvedSpellContextState = {
      context: null,
      error: null,
      loading: false,
    };
  });

  it("magia multi-instancia usa contexto pre-cast para mostrar InstanceTargetSelector", () => {
    resolvedSpellContextState = {
      context: {
        effect_instance_count: 5,
        effect_instance_dice: "1d4+1",
        damage_preview: "5d4+5",
      },
      error: null,
      loading: false,
    };

    const markup = renderToStaticMarkup(
      <PlayerSpellCastDialog
        {...baseProps}
        spell={{
          id: "spell-1",
          name: "Magic Missile",
          canonicalKey: "magic_missile",
          campaignSpellId: null,
          level: 1,
          prepared: true,
          actionCost: "action",
          suggestedMode: "direct_damage",
          damageType: "Force",
          savingThrow: null,
          availableSlotLevels: [1, 2, 3],
          upcast: {
            mode: "additional_effect_instances",
            dice: "1d4+1",
            perLevel: 1,
            baseEffectInstances: 3,
          },
        }}
      />,
    );

    expect(markup).toContain("Alvos por instância");
    expect(markup).toContain("Míssil 1");
  });

  it("magia single-instance nao mostra InstanceTargetSelector quando o contexto pre-cast retorna 1 instancia", () => {
    resolvedSpellContextState = {
      context: {
        effect_instance_count: 1,
        effect_instance_dice: null,
        damage_preview: "2d6",
      },
      error: null,
      loading: false,
    };

    const markup = renderToStaticMarkup(
      <PlayerSpellCastDialog
        {...baseProps}
        spell={{
          id: "spell-2",
          name: "Acid Splash",
          canonicalKey: "acid_splash",
          campaignSpellId: null,
          level: 0,
          prepared: true,
          actionCost: "action",
          suggestedMode: "saving_throw",
          damageType: "Acid",
          savingThrow: "DEX",
          availableSlotLevels: [],
        }}
      />,
    );

    expect(markup).not.toContain("Alvos por instância");
  });

  it("usa contexto pre-cast para renderizar Eldritch Blast nivel 5 com 2 linhas", () => {
    resolvedSpellContextState = {
      context: {
        effect_instance_count: 2,
        effect_instance_dice: "1d10",
        damage_preview: "2d10",
      },
      error: null,
      loading: false,
    };

    const markup = renderToStaticMarkup(
      <PlayerSpellCastDialog
        {...baseProps}
        spell={{
          id: "spell-3",
          name: "Eldritch Blast",
          canonicalKey: "eldritch_blast",
          campaignSpellId: null,
          level: 0,
          prepared: true,
          actionCost: "action",
          suggestedMode: "spell_attack",
          damageType: "Force",
          savingThrow: null,
          availableSlotLevels: [],
        }}
      />,
    );

    expect(markup).toContain("Feixe 1");
    expect(markup).toContain("Feixe 2");
  });

  it("resolve Magic Missile slot 3 com 5 instancias e Eldritch Blast nivel 5 com 2", () => {
    expect(
      resolveEffectInstanceContext(
        {
          level: 1,
          characterLevel: 5,
          cantripScaling: null,
          upcast: {
            mode: "additional_effect_instances",
            dice: "1d4+1",
            perLevel: 1,
            baseEffectInstances: 3,
          },
        },
        3,
      ),
    ).toEqual({
      instanceCount: 5,
      instanceDice: "1d4+1",
    });

    expect(
      resolveEffectInstanceContext(
        {
          level: 0,
          characterLevel: 5,
          upcast: null,
          cantripScaling: {
            scalingMode: "character_level",
            scalingEffectType: "effect_instances",
            thresholds: [
              { characterLevel: 1, instances: 1, instanceDamage: { dice: "1d10" } },
              { characterLevel: 5, instances: 2, instanceDamage: { dice: "1d10" } },
            ],
          },
        },
        null,
      ),
    ).toEqual({
      instanceCount: 2,
      instanceDice: "1d10",
    });
  });

  it("trocar slot de Magic Missile recalcula a quantidade de linhas e remove excedentes", () => {
    const slot1 = resolveEffectInstanceContext(
      {
        level: 1,
        characterLevel: 5,
        cantripScaling: null,
        upcast: {
          mode: "additional_effect_instances",
          dice: "1d4+1",
          perLevel: 1,
          baseEffectInstances: 3,
        },
      },
      1,
    );
    const slot3 = resolveEffectInstanceContext(
      {
        level: 1,
        characterLevel: 5,
        cantripScaling: null,
        upcast: {
          mode: "additional_effect_instances",
          dice: "1d4+1",
          perLevel: 1,
          baseEffectInstances: 3,
        },
      },
      3,
    );

    expect(slot1.instanceCount).toBe(3);
    expect(slot3.instanceCount).toBe(5);
    expect(
      reconcileEffectInstanceTargets(
        [
          { instance_index: 1, target_ref_id: "session_entity:goblin-a" },
          { instance_index: 2, target_ref_id: "session_entity:goblin-a" },
          { instance_index: 3, target_ref_id: "session_entity:goblin-b" },
          { instance_index: 4, target_ref_id: "session_entity:goblin-b" },
          { instance_index: 5, target_ref_id: "session_entity:goblin-c" },
        ],
        slot1.instanceCount,
      ),
    ).toEqual([
      { instance_index: 1, target_ref_id: "session_entity:goblin-a" },
      { instance_index: 2, target_ref_id: "session_entity:goblin-a" },
      { instance_index: 3, target_ref_id: "session_entity:goblin-b" },
    ]);
  });

  it("prefere o contexto backend e nao usa fallback local quando ele existe", () => {
    expect(
      getEffectiveEffectInstanceContext(
        {
          spell_id: "spell-1",
          spell_name: "Magic Missile",
          spell_level: 1,
          resolution_type: "direct_damage",
          requires_attack_roll: false,
          requires_saving_throw: false,
          effect_instance_count: 5,
          effect_instance_dice: "1d4+1",
          upcast_applied: true,
          upcast_added_instances: 2,
        },
        {
          instanceCount: 3,
          instanceDice: "1d4+1",
        },
        true,
      ),
    ).toEqual({
      instanceCount: 5,
      instanceDice: "1d4+1",
    });
  });

  it("queda do resolve-context usa fallback sem quebrar o dialogo", () => {
    resolvedSpellContextState = {
      context: null,
      error: "resolve failed",
      loading: false,
    };

    const markup = renderToStaticMarkup(
      <PlayerSpellCastDialog
        {...baseProps}
        spell={{
          id: "spell-1",
          name: "Magic Missile",
          canonicalKey: "magic_missile",
          campaignSpellId: null,
          level: 1,
          prepared: true,
          actionCost: "action",
          suggestedMode: "direct_damage",
          damageType: "Force",
          savingThrow: null,
          availableSlotLevels: [1, 2, 3],
          upcast: {
            mode: "additional_effect_instances",
            dice: "1d4+1",
            perLevel: 1,
            baseEffectInstances: 3,
          },
        }}
      />,
    );

    expect(markup).toContain("Alvos por instância");
    expect(markup).toContain("Míssil 1");
  });

  it("submit de Magic Missile e Eldritch Blast inclui effect_instance_targets", () => {
    const multiPayload = buildNonAreaSpellCastPayload({
      actorParticipantId: actor.id,
      concentrationManualRoll: null,
      concentrationRollMode: "system",
      effectInstanceTargets: [
        { instance_index: 1, target_ref_id: "session_entity:goblin-a" },
        { instance_index: 2, target_ref_id: "session_entity:goblin-a" },
        { instance_index: 3, target_ref_id: "session_entity:goblin-b" },
        { instance_index: 4, target_ref_id: "session_entity:goblin-b" },
        { instance_index: 5, target_ref_id: "session_entity:goblin-c" },
      ],
      isMultiInstanceSpell: true,
      parsedBonus: 0,
      selectedSlotLevel: 3,
      spell: {
        id: "spell-1",
        name: "Magic Missile",
        canonicalKey: "magic_missile",
        campaignSpellId: null,
        level: 1,
        prepared: true,
        actionCost: "action",
        suggestedMode: "direct_damage",
        damageType: "Force",
        savingThrow: null,
        availableSlotLevels: [1, 2, 3],
      },
      spellDamageType: "Force",
      spellEffectDice: "5d4+5",
      spellMode: "direct_damage",
      spellSaveAbility: "",
      targetRefId: "session_entity:goblin-a",
    });

    expect(multiPayload.effect_instance_targets).toHaveLength(5);
    expect(multiPayload.target_ref_id).toBe("session_entity:goblin-a");
  });

  it("submit de Acid Splash single-instance nao inclui effect_instance_targets", () => {
    const payload = buildNonAreaSpellCastPayload({
      actorParticipantId: actor.id,
      concentrationManualRoll: null,
      concentrationRollMode: "system",
      effectInstanceTargets: [],
      isMultiInstanceSpell: false,
      parsedBonus: 0,
      selectedSlotLevel: null,
      spell: {
        id: "spell-2",
        name: "Acid Splash",
        canonicalKey: "acid_splash",
        campaignSpellId: null,
        level: 0,
        prepared: true,
        actionCost: "action",
        suggestedMode: "saving_throw",
        damageType: "Acid",
        savingThrow: "DEX",
        availableSlotLevels: [],
      },
      spellDamageType: "Acid",
      spellEffectDice: "1d6",
      spellMode: "saving_throw",
      spellSaveAbility: "dexterity",
      targetRefId: "session_entity:goblin-a",
    });

    expect(payload.effect_instance_targets).toBeNull();
  });

  it("submit fica invalido quando ha instancias sem alvo", () => {
    resolvedSpellContextState = {
      context: {
        effect_instance_count: 5,
        effect_instance_dice: "1d4+1",
        damage_preview: "5d4+5",
      },
      error: null,
      loading: false,
    };

    renderToStaticMarkup(
      <PlayerSpellCastDialog
        {...baseProps}
        spell={{
          id: "spell-1",
          name: "Magic Missile",
          canonicalKey: "magic_missile",
          campaignSpellId: null,
          level: 1,
          prepared: true,
          actionCost: "action",
          suggestedMode: "direct_damage",
          damageType: "Force",
          savingThrow: null,
          availableSlotLevels: [1, 2, 3],
          upcast: {
            mode: "additional_effect_instances",
            dice: "1d4+1",
            perLevel: 1,
            baseEffectInstances: 3,
          },
        }}
      />,
    );

    expect(lastActionsProps?.submitDisabled).toBe(true);
    expect(lastActionsProps?.validationMessage).toBe("Escolha um alvo para cada instância da magia.");
  });
});
