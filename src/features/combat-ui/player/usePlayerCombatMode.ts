import { useEffect, useMemo, useRef, useState } from "react";
import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import { getBaseSpells, loadSpellCatalog } from "../../../entities/dnd-base";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { ITEM_TYPES } from "../../../entities/item";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import { localizedItemName } from "../../../features/shop/utils/localizedItemName";
import {
  combatRepo,
  type CombatAttackResult,
  type CombatParticipant,
  type CombatSpellMode,
  type CombatSpellResult,
  type StandardActionType,
} from "../../../shared/api/combatRepo";
import type { Locale } from "../../../shared/i18n";
import type { PlayerBoardStatusSummary } from "../../../pages/PlayerBoardPage/playerBoard.types";
import { useCombatUiState } from "../useCombatUiState";

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

export type CombatSpellOption = {
  canonicalKey: string | null;
  damageType: string | null;
  id: string;
  level: number;
  name: string;
  prepared: boolean;
  range: string;
  saveSuccessOutcome?: "none" | "half_damage" | null;
  savingThrow: string | null;
  suggestedMode: CombatSpellMode | null;
};

type Props = {
  campaignId?: string | null;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  locale: Locale;
  playerSheet?: CharacterSheet | null;
  playerStatus?: PlayerBoardStatusSummary | null;
  sessionId: string;
  userId?: string | null;
};

const buildSpellOptions = (
  playerSheet?: CharacterSheet | null,
  campaignId?: string | null,
): CombatSpellOption[] => {
  const spellcasting = playerSheet?.spellcasting;
  if (!spellcasting) return [];

  const catalog = getBaseSpells(campaignId);
  const byCanonicalKey = new Map(
    catalog.map((spell) => [spell.canonicalKey.toLowerCase(), spell] as const),
  );
  const byName = new Map(catalog.map((spell) => [spell.name.toLowerCase(), spell] as const));

  return spellcasting.spells
    .filter((spell) => spell.level === 0 || spell.prepared || spellcasting.mode === "known")
    .map((spell) => {
      const catalogSpell = spell.canonicalKey
        ? byCanonicalKey.get(spell.canonicalKey.toLowerCase()) ?? byName.get(spell.name.toLowerCase())
        : byName.get(spell.name.toLowerCase());
      const suggestedMode: CombatSpellMode | null = catalogSpell?.savingThrow
        ? "saving_throw"
        : catalogSpell?.damageType
          ? "spell_attack"
          : null;
      return {
        canonicalKey: spell.canonicalKey ?? catalogSpell?.canonicalKey ?? null,
        damageType: catalogSpell?.damageType ?? null,
        id: spell.id,
        level: spell.level,
        name: spell.name,
        prepared: spell.prepared,
        range: catalogSpell?.range ?? "",
        saveSuccessOutcome: catalogSpell?.saveSuccessOutcome ?? null,
        savingThrow: catalogSpell?.savingThrow ?? null,
        suggestedMode,
      };
    })
    .sort((left, right) => left.level - right.level || left.name.localeCompare(right.name));
};

type DeathSaveFeedback = {
  death_saves?: {
    failures?: number;
    successes?: number;
  };
  message?: string;
  roll?: number;
  status?: string;
};

export const usePlayerCombatMode = ({
  campaignId,
  inventory,
  itemsById,
  locale,
  playerSheet,
  playerStatus,
  sessionId,
  userId = null,
}: Props) => {
  const combat = useCombatUiState({ sessionId, userId });
  const [attackDialogOpen, setAttackDialogOpen] = useState(false);
  const [spellDialogOpen, setSpellDialogOpen] = useState(false);
  const [lastAttackResult, setLastAttackResult] = useState<CombatAttackResult | null>(null);
  const [lastSpellResult, setLastSpellResult] = useState<CombatSpellResult | null>(null);
  const [deathSaveFeedback, setDeathSaveFeedback] = useState<DeathSaveFeedback | null>(null);
  const [spellOptions, setSpellOptions] = useState<CombatSpellOption[]>([]);
  const [selectedSpellId, setSelectedSpellId] = useState("");
  const [spellMode, setSpellMode] = useState<CombatSpellMode>("spell_attack");
  const [spellEffectDice, setSpellEffectDice] = useState("");
  const [spellEffectBonus, setSpellEffectBonus] = useState("0");
  const [spellDamageType, setSpellDamageType] = useState("");
  const [spellSaveAbility, setSpellSaveAbility] = useState<AbilityName | "">("");
  const [targetId, setTargetId] = useState("");
  const [consumableItemId, setConsumableItemId] = useState("");
  const [useObjectNote, setUseObjectNote] = useState("");
  const previousPlayerStatusRef = useRef<
    Pick<PlayerBoardStatusSummary, "currentHp" | "deathSaveFailures" | "deathSaveSuccesses"> | null
  >(null);

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

  const selectedTarget = useMemo(() => {
    const allParticipants = [...combat.livingParticipants, ...combat.defeatedParticipants];
    return (
      allParticipants.find((participant) => participant.ref_id === targetId) ?? null
    );
  }, [combat.defeatedParticipants, combat.livingParticipants, targetId]);

  const withActionState = async (callback: () => Promise<void>) => {
    try {
      await callback();
    } catch (err: any) {
      throw new Error(err?.data?.detail || err?.message || "Combat action failed");
    }
  };

  const actorParticipantId = combat.myParticipant?.id ?? combat.currentParticipant?.id ?? null;

  const consumableOptions = useMemo(() => {
    return (inventory ?? [])
      .map((entry) => ({
        entry,
        item: itemsById[entry.itemId] ?? null,
      }))
      .filter((candidate) => candidate.item?.type === ITEM_TYPES.CONSUMABLE && candidate.entry.quantity > 0)
      .map((candidate) => ({
        id: candidate.entry.id,
        label: candidate.item
          ? `${localizedItemName(candidate.item, locale)} x${candidate.entry.quantity}`
          : `Item x${candidate.entry.quantity}`,
      }));
  }, [inventory, itemsById, locale]);

  useEffect(() => {
    if (!consumableOptions.length) {
      setConsumableItemId("");
      return;
    }
    setConsumableItemId((current) =>
      current && consumableOptions.some((option) => option.id === current)
        ? current
        : consumableOptions[0]!.id,
    );
  }, [consumableOptions]);

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
    const selectedConsumable = consumableOptions.find((option) => option.id === consumableItemId);
    const description = [
      selectedConsumable?.label,
      useObjectNote.trim() || null,
    ]
      .filter(Boolean)
      .join(" · ");
    await handleStandardAction("use_object", undefined, description || undefined);
    setUseObjectNote("");
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

  return {
    attackDialogOpen,
    closeAttackDialog: () => setAttackDialogOpen(false),
    closeSpellDialog: () => setSpellDialogOpen(false),
    combat,
    consumableItemId,
    consumableOptions,
    deathSaveFeedback,
    handleAttack,
    handleRequestReaction,
    handleDeathSave,
    handleEndTurn,
    handleStandardAction,
    handleUseObject,
    handleCast,
    lastAttackResult,
    lastSpellResult,
    selectedSpell,
    selectedSpellId,
    selectedTarget,
    setConsumableItemId,
    setLastAttackResult,
    setLastSpellResult,
    setSelectedSpellId,
    setSpellDamageType,
    setSpellEffectBonus,
    setSpellEffectDice,
    setSpellMode,
    setSpellSaveAbility,
    setTargetId,
    setUseObjectNote,
    spellDamageType,
    spellDialogOpen,
    spellEffectBonus,
    spellEffectDice,
    spellMode,
    spellOptions,
    spellSaveAbility,
    targetId,
    useObjectNote,
    visibleParticipants,
  };
};
