import { useEffect, useMemo, useRef, useState } from "react";
import {
  combatRepo,
  type CombatAttackResult,
  type CombatSpellMode,
  type CombatSpellResult,
  type CombatState,
  type StandardActionType
} from "../../../shared/api/combatRepo";
import { subscribe } from "../../../shared/realtime/centrifugoClient";
import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import {
  getBaseSpells,
  loadSpellCatalog,
  resolveSpellByAuthority
} from "../../../entities/dnd-base";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import {
  getCombatSpellAutomation,
  resolveCombatSpellActionCost
} from "../../../features/combat-ui/spellAutomation";
import { buildDragonbornBreathWeaponAction } from "../../../features/combat-ui/player/dragonbornBreathWeapon";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { PlayerBoardStatusSummary } from "../playerBoard.types";
import { spellRequiresExternalTarget } from "./areaTargetingUi";
import type { CombatSpellOption, DeathSaveFeedback } from "./types";

type Props = {
  campaignId?: string | null;
  playerSheet?: CharacterSheet | null;
  playerStatus?: PlayerBoardStatusSummary | null;
  sessionId: string;
};

const normalizeSavingThrow = (value?: string | null): AbilityName | "" => {
  const normalized = value?.trim().toLowerCase();
  switch (normalized) {
    case "str":
    case "strength":
      return "strength";
    case "dex":
    case "dexterity":
      return "dexterity";
    case "con":
    case "constitution":
      return "constitution";
    case "int":
    case "intelligence":
      return "intelligence";
    case "wis":
    case "wisdom":
      return "wisdom";
    case "cha":
    case "charisma":
      return "charisma";
    default:
      return "";
  }
};

const buildSpellOptions = (
  playerSheet?: CharacterSheet | null,
  campaignId?: string | null
): CombatSpellOption[] => {
  const spellcasting = playerSheet?.spellcasting;
  if (!spellcasting) return [];

  const catalog = getBaseSpells(campaignId);
  const availableSlotLevels = Object.entries(spellcasting.slots ?? {})
    .map(([level, slot]) => ({ level: Number(level), slot }))
    .filter(
      ({ level, slot }) =>
        Number.isInteger(level) && level > 0 && Boolean(slot?.max)
    )
    .map(({ level }) => level)
    .sort((left, right) => left - right);

  return spellcasting.spells
    .filter(
      (spell) =>
        spell.level === 0 || spell.prepared || spellcasting.mode === "known"
    )
    .map((spell) => {
      const catalogSpell = resolveSpellByAuthority(catalog, spell);
      const automation = getCombatSpellAutomation(
        spell.campaignSpellId
          ? (catalogSpell?.canonicalKey ?? spell.canonicalKey ?? null)
          : (spell.canonicalKey ?? catalogSpell?.canonicalKey ?? null)
      );
      const suggestedMode: CombatSpellMode | null =
        (catalogSpell?.attackType === "melee_spell" ||
        catalogSpell?.attackType === "ranged_spell"
          ? "spell_attack"
          : null) ??
        (catalogSpell?.effectTiming === "persistent" ||
        catalogSpell?.effectTiming === "triggered"
          ? "utility"
          : null) ??
        ((catalogSpell as { defaultSpellMode?: CombatSpellMode | null } | undefined)?.defaultSpellMode as
          | CombatSpellMode
          | null
          | undefined) ??
        automation?.defaultSpellMode ??
        (catalogSpell?.savingThrow
          ? "saving_throw"
          : catalogSpell?.resolutionType === "damage" || catalogSpell?.damageType
            ? "direct_damage"
            : null);
      return {
        id: spell.id,
        name: spell.name,
        canonicalKey: spell.campaignSpellId
          ? (catalogSpell?.canonicalKey ?? spell.canonicalKey ?? null)
          : (spell.canonicalKey ?? catalogSpell?.canonicalKey ?? null),
        campaignSpellId: spell.campaignSpellId ?? null,
        level: spell.level,
        prepared: spell.prepared,
        actionCost: resolveCombatSpellActionCost(
          catalogSpell?.castingTimeType ?? null
        ),
        suggestedMode,
        damageType: catalogSpell?.damageType ?? null,
        targetType: catalogSpell?.targetType ?? null,
        selectionType: catalogSpell?.selectionType ?? null,
        originType: catalogSpell?.originType ?? null,
        targetAnchor: catalogSpell?.targetAnchor ?? null,
        attackType: catalogSpell?.attackType ?? null,
        rangeKind: catalogSpell?.rangeKind ?? null,
        effectTiming: catalogSpell?.effectTiming ?? null,
        areaShape: catalogSpell?.areaShape ?? null,
        savingThrow: catalogSpell?.savingThrow ?? null,
        saveSuccessOutcome: catalogSpell?.saveSuccessOutcome ?? null,
        cantripScaling: catalogSpell?.cantripScaling ?? null,
        characterLevel: playerSheet?.level ?? null,
        availableSlotLevels:
          spell.level > 0
            ? availableSlotLevels.filter(
                (slotLevel) => slotLevel >= spell.level
              )
            : [],
        upcast: catalogSpell?.upcast ?? null,
        variants: (catalogSpell as { variants?: CombatSpellOption["variants"] } | undefined)?.variants ?? null,
      };
    })
    .sort(
      (left, right) =>
        left.level - right.level || left.name.localeCompare(right.name)
    );
};

export const usePlayerCombatDebugState = ({
  campaignId,
  playerSheet,
  playerStatus,
  sessionId
}: Props) => {
  const { t } = useLocale();
  const [state, setState] = useState<CombatState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [targetId, setTargetId] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"attack" | "cast">("attack");
  const [attackDialogOpen, setAttackDialogOpen] = useState(false);
  const [spellDialogOpen, setSpellDialogOpen] = useState(false);
  const [lastAttackResult, setLastAttackResult] =
    useState<CombatAttackResult | null>(null);
  const [lastSpellResult, setLastSpellResult] =
    useState<CombatSpellResult | null>(null);
  const [deathSaveFeedback, setDeathSaveFeedback] =
    useState<DeathSaveFeedback | null>(null);
  const [spellOptions, setSpellOptions] = useState<CombatSpellOption[]>([]);
  const [selectedSpellId, setSelectedSpellId] = useState<string>("");
  const [spellMode, setSpellMode] = useState<CombatSpellMode>("spell_attack");
  const [spellEffectDice, setSpellEffectDice] = useState<string>("");
  const [spellEffectBonus, setSpellEffectBonus] = useState<string>("0");
  const [spellDamageType, setSpellDamageType] = useState<string>("");
  const [spellSaveAbility, setSpellSaveAbility] = useState<AbilityName | "">(
    ""
  );
  const previousPlayerStatusRef = useRef<Pick<
    PlayerBoardStatusSummary,
    "currentHp" | "deathSaveFailures" | "deathSaveSuccesses"
  > | null>(null);

  useEffect(() => {
    let active = true;
    combatRepo
      .getState(sessionId)
      .then((nextState: CombatState) => {
        if (active) {
          setState(nextState);
        }
      })
      .catch(() => {
        if (active) {
          setState(null);
        }
      });

    const unsubscribe = subscribe(`session:${sessionId}`, {
      onPublication: (message: any) => {
        if (message?.type === "combat_state_updated") {
          setState(message.payload as CombatState);
          setError(null);
        }
      }
    });

    return () => {
      active = false;
      unsubscribe();
    };
  }, [sessionId]);

  useEffect(() => {
    let active = true;
    const rebuild = () => {
      if (active) {
        setSpellOptions(buildSpellOptions(playerSheet, campaignId));
      }
    };

    rebuild();
    if (!playerSheet?.spellcasting) {
      return () => {
        active = false;
      };
    }

    void loadSpellCatalog(campaignId)
      .then(rebuild)
      .catch(() => {
        rebuild();
      });

    return () => {
      active = false;
    };
  }, [campaignId, playerSheet]);

  useEffect(() => {
    if (!spellOptions.length) {
      setSelectedSpellId("");
      return;
    }
    setSelectedSpellId((current) =>
      current && spellOptions.some((spell) => spell.id === current)
        ? current
        : spellOptions[0]!.id
    );
  }, [spellOptions]);

  const selectedSpell = useMemo(
    () => spellOptions.find((spell) => spell.id === selectedSpellId) ?? null,
    [selectedSpellId, spellOptions]
  );
  const dragonbornBreathWeaponAction = useMemo(
    () => buildDragonbornBreathWeaponAction(playerSheet),
    [playerSheet]
  );

  useEffect(() => {
    if (!selectedSpell) {
      setSpellMode("spell_attack");
      setSpellDamageType("");
      setSpellSaveAbility("");
      return;
    }
    setSpellMode(selectedSpell.suggestedMode ?? "spell_attack");
    setSpellDamageType(selectedSpell.damageType ?? "");
    setSpellSaveAbility(normalizeSavingThrow(selectedSpell.savingThrow));
    setSpellEffectDice("");
    setSpellEffectBonus("0");
  }, [selectedSpell]);

  useEffect(() => {
    if (!playerStatus) {
      previousPlayerStatusRef.current = null;
      return;
    }

    const previous = previousPlayerStatusRef.current;
    const nextSnapshot = {
      currentHp: playerStatus.currentHp,
      deathSaveFailures: playerStatus.deathSaveFailures,
      deathSaveSuccesses: playerStatus.deathSaveSuccesses
    };

    if (!previous) {
      previousPlayerStatusRef.current = nextSnapshot;
      return;
    }

    const failureDelta =
      playerStatus.deathSaveFailures - previous.deathSaveFailures;
    if (failureDelta > 0 && playerStatus.currentHp <= 0) {
      setDeathSaveFeedback({
        death_saves: {
          failures: playerStatus.deathSaveFailures,
          successes: playerStatus.deathSaveSuccesses
        },
        message:
          failureDelta >= 2
            ? t("playerBoard.criticalHitWhileDowned")
            : t("playerBoard.damageWhileDowned"),
        status:
          playerStatus.deathSaveFailures >= 3
            ? "dead"
            : playerStatus.deathSaveSuccesses >= 3
              ? "stable"
              : "downed"
      });
    }

    previousPlayerStatusRef.current = nextSnapshot;
  }, [playerStatus]);

  const withActionState = async (callback: () => Promise<void>) => {
    setLoading(true);
    setError(null);
    try {
      await callback();
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Falha na ação de combate");
    } finally {
      setLoading(false);
    }
  };

  const getActorParticipantId = () =>
    state?.participants[state.current_turn_index]?.id ?? null;

  const handleAttack = async () => {
    if (!targetId || !state) return;
    setError(null);
    setLastAttackResult(null);
    setAttackDialogOpen(true);
  };

  const handleCast = async () => {
    if (!state || !selectedSpell) return;
    if (spellRequiresExternalTarget(selectedSpell.selectionType, selectedSpell.areaShape) && !targetId) return;
    setError(null);
    setLastSpellResult(null);
    setSpellDialogOpen(true);
  };

  const handleEndTurn = async () => {
    if (!state) return;
    await withActionState(async () => {
      const updated = await combatRepo.nextTurn(sessionId, {
        actor_participant_id: getActorParticipantId()
      });
      if (updated) {
        setState(updated);
      }
    });
  };

  const handleStandardAction = async (
    action: StandardActionType,
    targetParticipantId?: string,
    description?: string
  ) => {
    if (!state) return;
    await withActionState(async () => {
      await combatRepo.standardAction(sessionId, {
        action,
        actor_participant_id: getActorParticipantId(),
        target_participant_id: targetParticipantId,
        description
      });
    });
  };

  const handleDeathSave = async () => {
    if (!state) return;
    await withActionState(async () => {
      const result = await combatRepo.deathSave(sessionId, {
        actor_participant_id: getActorParticipantId()
      });
      setDeathSaveFeedback({
        ...(result ?? {}),
        message:
          result?.roll === 20
            ? t("playerBoard.criticalSuccessDeathSave")
            : result?.roll === 1
              ? t("playerBoard.criticalFailureDeathSave")
              : result?.status === "stable"
                ? t("playerBoard.stabilizedAtZero")
                : result?.status === "dead"
                  ? t("playerBoard.threeFailedDeathSaves")
                  : (result?.roll ?? 0) >= 10
                    ? t("playerBoard.deathSaveSucceeded")
                    : t("playerBoard.deathSaveFailed")
      });
    });
  };

  return {
    activeTab,
    attackDialogOpen,
    closeAttackDialog: () => setAttackDialogOpen(false),
    closeSpellDialog: () => setSpellDialogOpen(false),
    deathSaveFeedback,
    dragonbornBreathWeaponAction,
    error,
    handleAttack,
    handleAttackResolved: (result: CombatAttackResult) => {
      setLastAttackResult(result);
    },
    handleCast,
    handleDeathSave,
    handleEndTurn,
    handleStandardAction,
    lastAttackResult,
    lastSpellResult,
    loading,
    selectedSpell,
    selectedSpellId,
    setActiveTab,
    setSelectedSpellId,
    setSpellDamageType,
    setSpellEffectBonus,
    setSpellEffectDice,
    setSpellMode,
    setSpellSaveAbility,
    setTargetId,
    spellDamageType,
    spellDialogOpen,
    spellEffectBonus,
    spellEffectDice,
    spellMode,
    spellOptions,
    spellSaveAbility,
    state,
    targetId,
    handleSpellResolved: (result: CombatSpellResult) => {
      setLastSpellResult(result);
    }
  };
};
