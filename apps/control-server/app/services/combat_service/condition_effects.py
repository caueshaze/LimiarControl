"""condition_effects.py — Centralized condition-state resolver for Phase 12+.

All helpers are pure functions that operate on a participant dict (as stored in
CombatState.participants).  They have no DB dependency and no side effects.

Condition semantics follow D&D 5e SRD:
  - incapacitated: can't take actions or reactions; no movement
  - paralyzed:     incapacitated + auto-fail STR/DEX saves; attack rolls against
                    have advantage; hits from within 5 ft are critical
  - stunned:       incapacitated + auto-fail STR/DEX saves
  - unconscious:   incapacitated + prone + auto-fail STR/DEX saves
  - restrained:    speed 0; disadvantage on attacks + DEX saves; attacks
                    against have advantage
  - grappled:      speed 0
  - blinded:       can't see; auto-fail sight-based checks; attacks disadvantage
  - invisible:     unseen; attacks have advantage; attacks against have disadvantage
  - prone:         disadvantage on attacks; melee attacks within 5 ft have advantage;
                    ranged attacks against have disadvantage; movement costs double
  - frightened:    disadvantage on attacks when source is visible; can't move toward source
  - charmed:       can't attack charmer; charmer has advantage on social checks
  - deafened:      can't hear; auto-fail hearing-based checks
  - petrified:     incapacitated + can't move + no awareness
  - poisoned:      disadvantage on attacks and ability checks

Phase F1 adds a structured, source-based advantage resolver for attack rolls.
See ``resolve_attack_advantage`` and ``AttackAdvantageContext``.

Phase F2 extends mechanical effects:
  - ``get_attack_auto_crit``: melee hits against paralyzed/unconscious auto-crit.
  - ``modify_saving_throw``: condition-based save modifiers (auto-fail, dis/adv).

Phase F3 adds:
  - ``is_heavily_obscured``, ``is_lightly_obscured``: obscurement predicates.
  - Visibility-based disadvantage (blinded, invisible, obscured) is now
    resolved centrally in the visibility module and surfaced as
    ``attacker_cannot_directly_see_target`` by attack handlers.  These sources
    are intentionally excluded from ``resolve_attack_advantage`` to prevent
    double-counting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Low-level predicate
# ---------------------------------------------------------------------------


def has_condition(participant: dict, condition_type: str) -> bool:
    """Return True if the participant has an active condition effect of the given type."""
    for effect in participant.get("active_effects") or []:
        if (
            effect.get("kind") == "condition"
            and effect.get("condition_type") == condition_type
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Compound predicates
# ---------------------------------------------------------------------------

# Conditions that carry the incapacitated rule (can't take actions/reactions)
_INCAPACITATING_CONDITIONS = frozenset(
    {
        "incapacitated",
        "paralyzed",
        "stunned",
        "unconscious",
        "petrified",
    }
)

# Conditions that set speed to 0
_MOVEMENT_BLOCKING_CONDITIONS = frozenset(
    {
        "incapacitated",
        "paralyzed",
        "stunned",
        "unconscious",
        "petrified",
        "restrained",
        "grappled",
    }
)

# Conditions that halve speed (when not already blocked)
_MOVEMENT_HALVING_CONDITIONS = frozenset(
    {
        "prone",
    }
)


def is_action_blocked(participant: dict) -> bool:
    """Return True if the participant cannot take actions or reactions."""
    for effect in participant.get("active_effects") or []:
        if (
            effect.get("kind") == "condition"
            and effect.get("condition_type") in _INCAPACITATING_CONDITIONS
        ):
            return True
    return False


def is_movement_blocked(participant: dict) -> bool:
    """Return True if the participant's speed is reduced to 0."""
    for effect in participant.get("active_effects") or []:
        if (
            effect.get("kind") == "condition"
            and effect.get("condition_type") in _MOVEMENT_BLOCKING_CONDITIONS
        ):
            return True
    return False


def is_movement_halved(participant: dict) -> bool:
    """Return True if the participant's speed is halved (and not already blocked)."""
    if is_movement_blocked(participant):
        return False
    for effect in participant.get("active_effects") or []:
        if (
            effect.get("kind") == "condition"
            and effect.get("condition_type") in _MOVEMENT_HALVING_CONDITIONS
        ):
            return True
    return False


def can_see(participant: dict) -> bool:
    """Return False when the participant is blinded, unconscious, or petrified."""
    for effect in participant.get("active_effects") or []:
        ctype = (
            effect.get("condition_type") if effect.get("kind") == "condition" else None
        )
        if ctype in ("blinded", "unconscious", "petrified"):
            return False
    return True


def is_invisible(participant: dict) -> bool:
    """Return True when the participant is invisible."""
    return has_condition(participant, "invisible")


def is_heavily_obscured(participant: dict) -> bool:
    """Return True when the participant is heavily obscured (Phase F3)."""
    return has_condition(participant, "heavily_obscured")


def is_lightly_obscured(participant: dict) -> bool:
    """Return True when the participant is lightly obscured (Phase F3)."""
    return has_condition(participant, "lightly_obscured")


# ---------------------------------------------------------------------------
# Targeting modifiers
# ---------------------------------------------------------------------------


def get_attack_advantage_penalty(attacker: dict, target: dict) -> int:
    """DEPRECATED — thin wrapper kept for backward compatibility.

    New code should call ``resolve_attack_advantage`` instead and use the
    returned ``AttackAdvantageContext``.  This wrapper maps the structured
    result back to the old +1 / 0 / -1 convention.
    """
    ctx = resolve_attack_advantage(attacker, target, attack_kind="melee")
    if ctx.result == "advantage":
        return 1
    if ctx.result == "disadvantage":
        return -1
    return 0


# ---------------------------------------------------------------------------
# Phase F1 — structured attack-roll advantage resolver
# ---------------------------------------------------------------------------


@dataclass
class AttackAdvantageContext:
    """Structured advantage/disadvantage context for a single attack roll.

    Preserves every contributing source so that callers can log the reasons
    and future UI can display them without re-deriving the logic.

    Source identifiers are stable, readable strings such as:
      attacker_invisible, attacker_blinded, target_restrained, ...

    Resolution follows 5e cancellation rules:
      - any advantage source(s) + no disadvantage sources  → advantage
      - any disadvantage source(s) + no advantage sources  → disadvantage
      - at least one of each                               → normal
      - neither                                            → normal
    Sources do NOT stack numerically; existence is all that matters.
    """

    advantage_sources: list[str] = field(default_factory=list)
    disadvantage_sources: list[str] = field(default_factory=list)
    result: Literal["advantage", "normal", "disadvantage"] = "normal"

    def describe(self) -> str:
        """Compact one-line description suitable for combat logs.

        Examples:
          'advantage (attacker_invisible, target_restrained)'
          'disadvantage (attacker_blinded)'
          'normal (attacker_invisible canceled by target_prone_ranged)'
          'normal'
        """
        has_adv = bool(self.advantage_sources)
        has_dis = bool(self.disadvantage_sources)
        if self.result == "normal" and has_adv and has_dis:
            adv_str = ", ".join(self.advantage_sources)
            dis_str = ", ".join(self.disadvantage_sources)
            return f"normal ({adv_str} canceled by {dis_str})"
        sources = (
            self.advantage_sources
            if self.result == "advantage"
            else self.disadvantage_sources
        )
        if sources:
            return f"{self.result} ({', '.join(sources)})"
        return self.result


def resolve_attack_advantage(
    attacker: dict,
    target: dict,
    attack_kind: str = "melee",
) -> AttackAdvantageContext:
    """Return a structured :class:`AttackAdvantageContext` for an attack roll.

    ``attack_kind`` must be ``"melee"`` or ``"ranged"``.  It affects prone-target
    resolution: melee attacks against a prone target gain advantage, ranged
    attacks suffer disadvantage.

    This is the single source of truth for condition-based attack advantage and
    disadvantage.  Additional sources (effects, request flags) are handled by
    the callers and merged with the boolean result fields.
    """
    adv: list[str] = []
    dis: list[str] = []

    # ── Attacker: disadvantage sources ──────────────────────────────────────
    # NOTE (Phase F3): attacker_blinded and target_invisible are now resolved
    # through the centralized visibility module and surfaced as
    # attacker_cannot_directly_see_target by callers.  They must NOT be
    # duplicated here.
    if has_condition(attacker, "prone"):
        dis.append("attacker_prone")
    if has_condition(attacker, "frightened"):
        dis.append("attacker_frightened")
    if has_condition(attacker, "restrained"):
        dis.append("attacker_restrained")
    if has_condition(attacker, "poisoned"):
        dis.append("attacker_poisoned")

    # ── Attacker: advantage sources ──────────────────────────────────────────
    if is_invisible(attacker):
        adv.append("attacker_invisible")

    # ── Target conditions: advantage for the attacker ────────────────────────
    if has_condition(target, "restrained"):
        adv.append("target_restrained")
    if has_condition(target, "paralyzed"):
        adv.append("target_paralyzed")
    if has_condition(target, "stunned"):
        adv.append("target_stunned")
    if has_condition(target, "unconscious"):
        adv.append("target_unconscious")

    # ── Prone target: depends on attack kind ────────────────────────────────
    if has_condition(target, "prone"):
        if attack_kind == "melee":
            adv.append("target_prone_melee")
        else:
            dis.append("target_prone_ranged")

    # ── Resolution (5e cancellation rule) ───────────────────────────────────
    if adv and not dis:
        result: Literal["advantage", "normal", "disadvantage"] = "advantage"
    elif dis and not adv:
        result = "disadvantage"
    else:
        result = "normal"

    return AttackAdvantageContext(
        advantage_sources=adv,
        disadvantage_sources=dis,
        result=result,
    )


# ---------------------------------------------------------------------------
# Phase F2 — auto-crit and saving-throw modifiers
# ---------------------------------------------------------------------------

# Conditions that cause auto-fail on STR and DEX saving throws.
_AUTO_FAIL_SAVE_CONDITIONS = frozenset({"paralyzed", "stunned", "unconscious"})

# Abilities affected by the auto-fail conditions above.
_AUTO_FAIL_SAVE_ABILITIES = frozenset({"strength", "dexterity"})


def get_attack_auto_crit(
    attacker: dict,  # noqa: ARG001 — reserved for future attacker-side checks
    target: dict,
    attack_kind: str = "melee",
) -> str:
    """Return a stable source label if the hit must be treated as a critical.

    D&D 5e SRD: melee attacks that hit a paralyzed or unconscious target
    automatically score a critical hit (the attacker is within 5 ft).

    Returns:
        ``"target_paralyzed"`` or ``"target_unconscious"`` when auto-crit
        applies; ``""`` (falsy empty string) otherwise.

    Only applies to melee attacks.  Ranged attacks and spell attacks are
    not affected regardless of target conditions.
    """
    if attack_kind != "melee":
        return ""
    if has_condition(target, "paralyzed"):
        return "target_paralyzed"
    if has_condition(target, "unconscious"):
        return "target_unconscious"
    return ""


@dataclass
class SaveModifierContext:
    """Condition-based modifiers for a single saving throw.

    Structurally mirrors :class:`AttackAdvantageContext` for consistency and
    forward-compatibility.

    ``auto_fail``            — the throw is automatically failed regardless of roll.
    ``auto_fail_source``     — stable source label when auto_fail is True.
    ``advantage_sources``    — list of stable source labels granting advantage.
    ``disadvantage_sources`` — list of stable source labels granting disadvantage.
    ``result``               — resolved mode after 5e cancellation rules; ignored
                               when ``auto_fail`` is True.

    Resolution rules (same as AttackAdvantageContext):
      - auto_fail → result is irrelevant; auto_fail takes absolute priority.
      - ≥1 advantage source + no disadvantage → result = "advantage".
      - ≥1 disadvantage source + no advantage → result = "disadvantage".
      - at least one of each, or neither              → result = "normal".
    """

    auto_fail: bool = False
    auto_fail_source: str = ""
    advantage_sources: list[str] = field(default_factory=list)
    disadvantage_sources: list[str] = field(default_factory=list)
    result: Literal["advantage", "normal", "disadvantage"] = "normal"


def modify_saving_throw(actor: dict, ability: str) -> SaveModifierContext:
    """Return condition-based modifiers for a saving throw made by *actor*.

    ``ability`` must be a lowercase English ability name as used throughout
    the codebase (e.g. ``"strength"``, ``"dexterity"``, ``"constitution"``).

    Rules implemented (5e SRD subset):
      - paralyzed / stunned / unconscious → auto-fail STR and DEX saves.
      - restrained → disadvantage on DEX saves.

    The returned context is applied by the caller:
      - If ``auto_fail`` is True, treat the save as failed regardless of roll.
      - Otherwise pass ``result`` to ``resolve_saving_throw`` as the advantage mode.
    """
    normalized = ability.lower()

    # Auto-fail: paralyzed / stunned / unconscious on STR or DEX
    if normalized in _AUTO_FAIL_SAVE_ABILITIES:
        for cond in _AUTO_FAIL_SAVE_CONDITIONS:
            if has_condition(actor, cond):
                return SaveModifierContext(
                    auto_fail=True,
                    auto_fail_source=f"actor_{cond}",
                )

    adv: list[str] = []
    dis: list[str] = []

    # Restrained → disadvantage on DEX saves
    if normalized == "dexterity" and has_condition(actor, "restrained"):
        dis.append("actor_restrained")

    if adv and not dis:
        _result: Literal["advantage", "normal", "disadvantage"] = "advantage"
    elif dis and not adv:
        _result = "disadvantage"
    else:
        _result = "normal"

    return SaveModifierContext(
        advantage_sources=adv,
        disadvantage_sources=dis,
        result=_result,
    )


# ---------------------------------------------------------------------------
# Spell attack kind resolver
# ---------------------------------------------------------------------------


def resolve_spell_attack_kind(spell_or_action: dict | None = None) -> str:
    """Return the attack kind for a spell attack roll.

    This is the single source of truth for spell-attack kind resolution.
    Currently all spell attacks are treated as ranged (beam, bolt, etc.).
    Future phases may inspect spell metadata to detect melee spell attacks
    (e.g. Shocking Grasp) by reading ``spell_or_action.get("attackKind")``
    or ``spell_or_action.get("rangeType")``.

    Args:
        spell_or_action: Optional spell or resolved-action dict.  Reserved for
                         future metadata inspection — currently ignored.

    Returns:
        ``"ranged"`` (always, for now).
    """
    # Future hook: inspect spell_or_action metadata when melee spell attacks land.
    return "ranged"


# ---------------------------------------------------------------------------
# Reach helper
# ---------------------------------------------------------------------------


def get_effective_reach(base_reach_cells: int) -> int:
    """Return effective reach in cells.

    Delegates to the centralized reach module (Phase F4).
    Kept here for backward compatibility; new code should import from
    ``reach`` directly.
    """
    from .reach import get_effective_reach as _reach

    return _reach(base_reach_cells)
