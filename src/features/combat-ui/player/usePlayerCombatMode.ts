import { useEffect, useMemo, useRef, useState } from "react";
import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import {
  combatRepo,
  type CombatAttackResult,
  type CombatSpellMode,
  type CombatSpellResult,
  type CombatStandardActionResult,
  type StandardActionType,
} from "../../../shared/api/combatRepo";
import type { PlayerBoardStatusSummary } from "../../../pages/PlayerBoardPage/playerBoard.types";
import { useCombatUiState } from "../useCombatUiState";
import {
  buildSpellOptions,
  loadSpellCatalog,
  normalizeSavingThrow,
  withActionState,
} from "./usePlayerCombatModeHelpers";
import { buildDragonbornBreathWeaponAction } from "./dragonbornBreathWeapon";
import { useConsumables } from "./useConsumables";
import type {
  CombatSpellOption,
  DeathSaveFeedback,
  UsePlayerCombatModeProps,
} from "./usePlayerCombatMode.types";

export type { CombatSpellOption, CombatConsumableOption } from "./usePlayerCombatMode.types";

export const usePlayerCombatMode = ({
  campaignId,
  inventory,
  itemsById,
  locale,
  playerSheet,
  playerStatus,
  sessionId,
  userId = null,
}: UsePlayerCombatModeProps) => {
  const combat = useCombatUiState({ sessionId, userId });
  const [attackDialogOpen, setAttackDialogOpen] = useState(false);
  const [spellDialogOpen, setSpellDialogOpen] = useState(false);
  const [lastAttackResult, setLastAttackResult] = useState<CombatAttackResult | null>(null);
  const [lastSpellResult, setLastSpellResult] = useState<CombatSpellResult | null>(null);
  const [lastUseObjectResult, setLastUseObjectResult] = useState<CombatStandardActionResult | null>(
    null,
  );
  const [deathSaveFeedback, setDeathSaveFeedback] = useState<DeathSaveFeedback | null>(null);
  const [spellOptions, setSpellOptions] = useState<CombatSpellOption[]>([]);
  const [selectedSpellId, setSelectedSpellId] = useState("");
  const [spellMode, setSpellMode] = useState<CombatSpellMode>("spell_attack");
  const [spellEffectDice, setSpellEffectDice] = useState("");
  const [spellEffectBonus, setSpellEffectBonus] = useState("0");
  const [spellDamageType, setSpellDamageType] = useState("");
  const [spellSaveAbility, setSpellSaveAbility] = useState<AbilityName | "">("");
  const [targetId, setTargetId] = useState("");
  const previousPlayerStatusRef = useRef<
    Pick<PlayerBoardStatusSummary, "currentHp" | "deathSaveFailures" | "deathSaveSuccesses"> | null
  >(null);

  // ── Spell catalog loading ──────────────────────────────────────────────────

  useEffect(() => {
    let active = true;
    const rebuild = () => {
      if (active) {
        setSpellOptions(buildSpellOptions(playerSheet, campaignId, inventory, itemsById));
      }
    };
    rebuild();
    const hasMagicItemSpells = (inventory ?? []).some((entry) => {
      const item = itemsById[entry.itemId];
      return item?.magicEffect?.type === "cast_spell";
    });
    if (!playerSheet?.spellcasting && !hasMagicItemSpells) {
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
  }, [campaignId, inventory, itemsById, playerSheet]);

  useEffect(() => {
    if (!spellOptions.length) {
      setSelectedSpellId("");
      return;
    }
    setSelectedSpellId((current) =>
      current && spellOptions.some((spell) => spell.id === current) ? current : spellOptions[0]!.id,
    );
  }, [spellOptions]);

  const selectedSpell = useMemo(
    () => spellOptions.find((spell) => spell.id === selectedSpellId) ?? null,
    [selectedSpellId, spellOptions],
  );

  useEffect(() => {
    if (!selectedSpell) {
      setSpellMode("spell_attack");
      setSpellDamageType("");
      setSpellSaveAbility("");
      setSpellEffectDice("");
      setSpellEffectBonus("0");
      return;
    }
    setSpellMode(selectedSpell.suggestedMode ?? "spell_attack");
    setSpellDamageType(selectedSpell.damageType ?? "");
    setSpellSaveAbility(normalizeSavingThrow(selectedSpell.savingThrow));
    setSpellEffectDice("");
    setSpellEffectBonus("0");
  }, [selectedSpell]);

  // ── Death save tracking ────────────────────────────────────────────────────

  useEffect(() => {
    if (!playerStatus) {
      previousPlayerStatusRef.current = null;
      return;
    }
    const previous = previousPlayerStatusRef.current;
    const nextSnapshot = {
      currentHp: playerStatus.currentHp,
      deathSaveFailures: playerStatus.deathSaveFailures,
      deathSaveSuccesses: playerStatus.deathSaveSuccesses,
    };
    if (!previous) {
      previousPlayerStatusRef.current = nextSnapshot;
      return;
    }
    const failureDelta = playerStatus.deathSaveFailures - previous.deathSaveFailures;
    if (failureDelta > 0 && playerStatus.currentHp <= 0) {
      setDeathSaveFeedback({
        death_saves: {
          failures: playerStatus.deathSaveFailures,
          successes: playerStatus.deathSaveSuccesses,
        },
        message:
          failureDelta >= 2
            ? "Critical hit while downed. Two failures added."
            : "Damage while downed. One failure added.",
        status:
          playerStatus.deathSaveFailures >= 3
            ? "dead"
            : playerStatus.deathSaveSuccesses >= 3
              ? "stable"
              : "downed",
      });
    }
    previousPlayerStatusRef.current = nextSnapshot;
  }, [playerStatus]);

  // ── Derived state ──────────────────────────────────────────────────────────

  const selectedTarget = useMemo(() => {
    const allParticipants = [...combat.livingParticipants, ...combat.defeatedParticipants];
    return allParticipants.find((participant) => participant.ref_id === targetId) ?? null;
  }, [combat.defeatedParticipants, combat.livingParticipants, targetId]);
  const dragonbornBreathWeaponAction = useMemo(
    () => buildDragonbornBreathWeaponAction(playerSheet),
    [playerSheet],
  );

  const actorParticipant = combat.myParticipant ?? combat.currentParticipant ?? null;
  const actorParticipantId = actorParticipant?.id ?? null;

  const visibleParticipants = useMemo(
    () =>
      (combat.state?.participants ?? []).filter(
        (participant) =>
          participant.kind === "player" ||
          participant.actor_user_id === userId ||
          participant.visible !== false,
      ),
    [combat.state?.participants, userId],
  );

  // ── Consumables ────────────────────────────────────────────────────────────

  const consumables = useConsumables({
    actorParticipant,
    actorParticipantId,
    inventory,
    itemsById,
    locale,
    participants: combat.state?.participants ?? [],
  });

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleAttack = async () => {
    if (!targetId || !combat.state) return;
    setLastAttackResult(null);
    setAttackDialogOpen(true);
  };

  const handleCast = async () => {
    if (!targetId || !combat.state || !selectedSpell) return;
    setLastSpellResult(null);
    setSpellDialogOpen(true);
  };

  const handleEndTurn = async () => {
    if (!combat.state || !actorParticipantId) return;
    await withActionState(async () => {
      const updated = await combatRepo.nextTurn(sessionId, {
        actor_participant_id: actorParticipantId,
      });
      if (updated) {
        await combat.refreshState();
      }
    });
  };

  const handleStandardAction = async (
    action: StandardActionType,
    targetParticipantId?: string,
    description?: string,
  ) => {
    if (!actorParticipantId) return;
    await withActionState(async () => {
      await combatRepo.standardAction(sessionId, {
        action,
        actor_participant_id: actorParticipantId,
        description,
        target_participant_id: targetParticipantId,
      });
      await combat.refreshState();
    });
  };

  const handleUseObject = async () => {
    const { selectedConsumable, useObjectNote, useObjectTargetParticipantId, useObjectRollMode, useObjectManualRolls } = consumables;
    const description = [selectedConsumable?.label, useObjectNote.trim() || null]
      .filter(Boolean)
      .join(" · ");
    if (!actorParticipantId) return;
    setLastUseObjectResult(null);

    if (!selectedConsumable?.isHealingConsumable) {
      await withActionState(async () => {
        const result = await combatRepo.standardAction(sessionId, {
          action: "use_object",
          actor_participant_id: actorParticipantId,
          description: description || undefined,
        });
        setLastUseObjectResult(result);
        await combat.refreshState();
      });
      consumables.setUseObjectNote("");
      return;
    }

    await withActionState(async () => {
      const result = await combatRepo.standardAction(sessionId, {
        action: "use_object",
        actor_participant_id: actorParticipantId,
        inventory_item_id: selectedConsumable.id,
        target_participant_id: useObjectTargetParticipantId || actorParticipantId,
        roll_source: useObjectRollMode,
        manual_rolls: useObjectRollMode === "manual" ? useObjectManualRolls : null,
      });
      setLastUseObjectResult(result);
      await combat.refreshState();
    });
    consumables.setUseObjectManualRolls([]);
    consumables.setUseObjectNote("");
  };

  const handleDragonbornBreathWeapon = async () => {
    if (!actorParticipantId || !selectedTarget?.id) return;
    await withActionState(async () => {
      await combatRepo.standardAction(sessionId, {
        action: "dragonborn_breath_weapon",
        actor_participant_id: actorParticipantId,
        target_participant_id: selectedTarget.id,
      });
      await combat.refreshState();
    });
  };

  const handleDeathSave = async () => {
    if (!actorParticipantId) return;
    await withActionState(async () => {
      const result = await combatRepo.deathSave(sessionId, {
        actor_participant_id: actorParticipantId,
      });
      setDeathSaveFeedback({
        ...(result ?? {}),
        message:
          result?.roll === 20
            ? "Critical success. You return with 1 HP."
            : result?.roll === 1
              ? "Critical failure. Two failures were added."
              : result?.status === "stable"
                ? "You stabilized at 0 HP."
                : result?.status === "dead"
                  ? "You reached 3 failed death saves."
                  : (result?.roll ?? 0) >= 10
                    ? "Death save succeeded."
                    : "Death save failed.",
      });
      await combat.refreshState();
    });
  };

  const handleRequestReaction = async () => {
    const participantId = combat.myParticipant?.id;
    if (!participantId) return;
    await withActionState(async () => {
      await combatRepo.requestReaction(sessionId, {
        actor_participant_id: participantId,
      });
      await combat.refreshState();
    });
  };

  return {
    attackDialogOpen,
    closeAttackDialog: () => setAttackDialogOpen(false),
    closeSpellDialog: () => setSpellDialogOpen(false),
    combat,
    deathSaveFeedback,
    dragonbornBreathWeaponAction,
    handleAttack,
    handleDragonbornBreathWeapon,
    handleRequestReaction,
    handleDeathSave,
    handleEndTurn,
    handleStandardAction,
    handleUseObject,
    handleCast,
    lastAttackResult,
    lastSpellResult,
    lastUseObjectResult,
    selectedSpell,
    selectedSpellId,
    selectedTarget,
    setLastAttackResult,
    setLastSpellResult,
    setLastUseObjectResult,
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
    targetId,
    visibleParticipants,
    // consumables (spread para manter a mesma superfície pública)
    ...consumables,
  };
};
