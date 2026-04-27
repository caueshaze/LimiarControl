from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.roll import RollResult


@dataclass
class SpellResolutionResult:
    roll_result: RollResult | None = None
    roll_total: int | None = None
    is_critical: bool = False
    is_hit: bool | None = None
    is_saved: bool | None = None
    target_ac: int | None = None
    base_ac: int | None = None
    base_save_dc: int | None = None
    cover: object = None
    cover_modifier: int = 0
    effective_dc: int = 0
    pending_spell_id: str | None = None
    pending_save_id: str | None = None
    damage: int = 0
    healing: int = 0
    new_hp: int | None = None
    effect_msg: str = ""
    previous_hp: int | None = None
    concentration_check: dict | None = None
    rolled_effect_total: int | None = None
    adv_ctx: object = None
    vis_ctx: object = None


class SpellResolutionCommonMixin:
    @classmethod
    def _apply_spell_effect(
        cls,
        db: Session,
        state: CombatState,
        target_ref_id: str,
        target_kind: str,
        effect_kind: str,
        amount: int,
        *,
        damage_type: str | None = None,
        is_critical: bool = False,
        concentration_roll_source: str = "system",
        concentration_manual_roll: int | None = None,
    ) -> tuple[int | None, str, int | None, dict | None]:
        if amount <= 0:
            return None, "", None, None
        if effect_kind == "healing":
            new_hp, effect_msg, previous_hp = cls._apply_healing_to_target(db, target_ref_id, target_kind, amount, state)
            return new_hp, effect_msg, previous_hp, None
        return cls._apply_damage_to_target(
            db,
            target_ref_id,
            target_kind,
            amount,
            damage_type=damage_type,
            is_crit=is_critical,
            state=state,
            **cls._build_concentration_roll_kwargs(concentration_roll_source, concentration_manual_roll),
        )

    @classmethod
    def _build_pending_spell_payload(
        cls,
        spell_context: dict,
        target_p: dict,
        *,
        action_kind: str,
        effect_kind: str | None,
        effect_bonus: int,
        save_success_outcome: str | None = None,
        is_saved: bool | None = None,
        is_critical: bool = False,
        roll_total: int | None = None,
        roll_result: RollResult | None = None,
        target_ac: int | None = None,
        effective_dc: int | None = None,
    ) -> dict:
        base = {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": action_kind,
            "effect_kind": effect_kind,
            "effect_dice": spell_context["effect_dice"],
            "effect_bonus": effect_bonus,
            "damage_type": spell_context.get("damage_type"),
            "elemental_affinity_eligible": spell_context.get("elemental_affinity_eligible"),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
            "target_ref_id": target_p["ref_id"],
            "target_kind": target_p["kind"],
            "target_display_name": target_p["display_name"],
            "save_ability": spell_context.get("save_ability"),
            "save_dc": effective_dc if effective_dc is not None else spell_context.get("save_dc"),
            "is_critical": is_critical,
            "roll": roll_total,
            "roll_result": roll_result.model_dump(mode="json") if roll_result else None,
        }
        if target_ac is not None:
            base["target_ac"] = target_ac
        if save_success_outcome is not None:
            base["save_success_outcome"] = save_success_outcome
        if is_saved is not None:
            base["is_saved"] = is_saved
        return base
