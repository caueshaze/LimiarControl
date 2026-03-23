import { useEffect, useMemo, useRef, useState } from "react";
import {
  combatRepo,
  type CombatAttackResult,
  type CombatSpellMode,
  type CombatSpellResult,
  type CombatState,
} from "../../../shared/api/combatRepo";
import { subscribe } from "../../../shared/realtime/centrifugoClient";
import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import { getBaseSpells, loadSpellCatalog } from "../../../entities/dnd-base";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import type { PlayerBoardStatusSummary } from "../playerBoard.types";
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
      const catalogSpell =
        (spell.canonicalKey && byCanonicalKey.get(spell.canonicalKey.toLowerCase())) ??
        byName.get(spell.name.toLowerCase());
      const suggestedMode: CombatSpellMode | null = catalogSpell?.savingThrow
        ? "saving_throw"
        : catalogSpell?.damageType
          ? "spell_attack"
          : null;
      return {
        id: spell.id,
        name: spell.name,
        canonicalKey: spell.canonicalKey ?? catalogSpell?.canonicalKey ?? null,
        level: spell.level,
        prepared: spell.prepared,
        suggestedMode,
        damageType: catalogSpell?.damageType ?? null,
        savingThrow: catalogSpell?.savingThrow ?? null,
      };
    })
    .sort((left, right) => left.level - right.level || left.name.localeCompare(right.name));
};

export const usePlayerCombatDebugState = ({
  campaignId,
  playerSheet,
  playerStatus,
  sessionId,
}: Props) => {
  const [state, setState] = useState<CombatState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [targetId, setTargetId] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"attack" | "cast">("attack");
  const [attackDialogOpen, setAttackDialogOpen] = useState(false);
  const [spellDialogOpen, setSpellDialogOpen] = useState(false);
  const [lastAttackResult, setLastAttackResult] = useState<CombatAttackResult | null>(null);
  const [lastSpellResult, setLastSpellResult] = useState<CombatSpellResult | null>(null);
  const [deathSaveFeedback, setDeathSaveFeedback] = useState<DeathSaveFeedback | null>(null);
  const [spellOptions, setSpellOptions] = useState<CombatSpellOption[]>([]);
  const [selectedSpellId, setSelectedSpellId] = useState<string>("");
  const [spellMode, setSpellMode] = useState<CombatSpellMode>("spell_attack");
  const [spellEffectDice, setSpellEffectDice] = useState<string>("");
  const [spellEffectBonus, setSpellEffectBonus] = useState<string>("0");
  const [spellDamageType, setSpellDamageType] = useState<string>("");
  const [spellSaveAbility, setSpellSaveAbility] = useState<AbilityName | "">("");
  const previousPlayerStatusRef = useRef<
    Pick<PlayerBoardStatusSummary, "currentHp" | "deathSaveFailures" | "deathSaveSuccesses"> | null
  >(null);

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
      },
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
            ? "You took a critical hit while downed. +2 failures."
            : "You took damage while downed. +1 failure.",
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

  const withActionState = async (callback: () => Promise<void>) => {
    setLoading(true);
    setError(null);
    try {
      await callback();
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Combat action failed");
    } finally {
      setLoading(false);
    }
  };

  const getActorParticipantId = () => state?.participants[state.current_turn_index]?.id ?? null;

  const handleAttack = async () => {
    if (!targetId || !state) return;
    setError(null);
    setLastAttackResult(null);
    setAttackDialogOpen(true);
  };

  const handleCast = async () => {
    if (!targetId || !state || !selectedSpell) return;
    setError(null);
    setLastSpellResult(null);
    setSpellDialogOpen(true);
  };

  const handleEndTurn = async () => {
    if (!state) return;
    await withActionState(async () => {
      const updated = await combatRepo.nextTurn(sessionId, {
        actor_participant_id: getActorParticipantId(),
      });
      if (updated) {
        setState(updated);
      }
    });
  };

  const handleDeathSave = async () => {
    if (!state) return;
    await withActionState(async () => {
      const result = await combatRepo.deathSave(sessionId, {
        actor_participant_id: getActorParticipantId(),
      });
      setDeathSaveFeedback({
        ...(result ?? {}),
        message:
          result?.roll === 20
            ? "Critical success. You are back up with 1 HP."
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
    });
  };

  return {
    activeTab,
    attackDialogOpen,
    closeAttackDialog: () => setAttackDialogOpen(false),
    closeSpellDialog: () => setSpellDialogOpen(false),
    deathSaveFeedback,
    error,
    handleAttack,
    handleAttackResolved: (result: CombatAttackResult) => {
      setLastAttackResult(result);
    },
    handleCast,
    handleDeathSave,
    handleEndTurn,
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
    },
  };
};
